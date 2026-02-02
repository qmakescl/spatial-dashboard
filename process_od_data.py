import pandas as pd
import json
import os
import sys

# Configuration
DATA_DIR = "datasets/popMove/houseHold"
OUTPUT_FILE = "dashboard/public/od_data.json"

def process_od_data():
    print("Starting OD data processing...")
    
    # Define columns: 
    # V1(Sido_In), V2(Sgg_In), V7(Sido_Out), V8(Sgg_Out), V15(Count)
    # Indices: 0, 1, 6, 7, 14
    cols = [0, 1, 6, 7, 14]
    col_names = ['target_sido', 'target_sgg', 'source_sido', 'source_sgg', 'count']
    col_types = {
        'target_sido': str, 'target_sgg': str, 
        'source_sido': str, 'source_sgg': str, 
        'count': float
    }
    
    # helper to clean and combine
    def process_df(df_raw):
        # Concatenate to 5-digit code
        df_raw['target'] = df_raw['target_sido'] + df_raw['target_sgg']
        df_raw['source'] = df_raw['source_sido'] + df_raw['source_sgg']
        # Filter intra-region moves
        df_raw = df_raw[df_raw['source'] != df_raw['target']]
        # Aggregate: count sum (people) AND size (households)
        agg = df_raw.groupby(['source', 'target'])['count'].agg(['sum', 'size']).reset_index()
        agg.rename(columns={'sum': 'count', 'size': 'hh_cnt'}, inplace=True)
        return agg

    # 1. Process 2023 Data
    print("Loading 2023 data...")
    path_2023 = os.path.join(DATA_DIR, "2023.csv")
    if not os.path.exists(path_2023):
        print(f"Error: 2023 file not found at {path_2023}")
        return
        
    df_raw_2023 = pd.read_csv(path_2023, header=None, usecols=cols, names=col_names, dtype=col_types)
    agg_2023 = process_df(df_raw_2023)
    print(f"2023 processed records: {len(agg_2023)}")

    # 2. Process 2024 Data
    print("Loading 2024 data...")
    path_2024 = os.path.join(DATA_DIR, "2024.csv")
    if not os.path.exists(path_2024):
        print(f"Error: 2024 file not found at {path_2024}")
        return

    df_raw_2024 = pd.read_csv(path_2024, header=None, usecols=cols, names=col_names, dtype=col_types)
    agg_2024 = process_df(df_raw_2024)
    print(f"2024 processed records: {len(agg_2024)}")
    
    # ---------------------------------------------------------
    # [NEW] Standardize 2023 Data to match 2024 Codes
    # ---------------------------------------------------------
    print("Standardizing 2023 data to 2024 codes...")
    
    # 1. Calculate Bucheon Ratios from 2024 Data
    # Bucheon Districts: Wonmi(41192), Sosa(41194), Ojeong(41196)
    # Target Code for 2023: Bucheon(41190)
    bucheon_codes = ['41192', '41194', '41196']
    
    # Calculate Total HH Count for each district across all flows to get a relative size
    # We use 'hh_cnt' (households) as it's a stable proxy for size
    # Summing up all 'inflow' + 'outflow' might be a good proxy for district size.
    # Alternatively, use 'target' (inflow) sums as proxy for residential size.
    
    # Let's use summed hh_cnt where district is TARGET (Inflow/Resident base approximation)
    b_stats = agg_2024[agg_2024['target'].isin(bucheon_codes)].groupby('target')['hh_cnt'].sum()
    b_total = b_stats.sum()
    
    if b_total > 0:
        bucheon_ratios = b_stats / b_total
        print("Bucheon Split Ratios (based on 2024 HH inflow):")
        print(bucheon_ratios)
    else:
        print("Warning: No Bucheon data in 2024. Using equal split.")
        bucheon_ratios = pd.Series({c: 1/3 for c in bucheon_codes})

    # Prepare 2023 rows for split
    # We need to act on rows where source or target is 41190
    
    new_rows = []
    
    # 2. 1:1 Mapping Logic (Jeonbuk, Gunwi)
    # Jeonbuk: 45xxx -> 52xxx
    # Gunwi: 47720 -> 27720
    
    def map_code(code):
        # Gunwi
        if code == '47720': return '27720'
        # Jeonbuk (Check prefix 45) - Jeonbuk codes are 45110~45790 etc.
        # But wait, we need to be careful not to map non-Jeonbuk 45 (none exist, 45 is Jeonbuk Sido)
        if code.startswith('45'):
            return '52' + code[2:]
        return code

    # It is faster to modify in place or rebuild. Let's rebuild to handle splitting cleanly.
    
    # Optimized approach:
    # A. Apply 1:1 Map to whole DF
    # B. Split Bucheon rows
    
    # A. Apply 1:1 Map
    # Note: 'source' and 'target' are series.
    # We can use apply, but string ops are slow.
    # Given limited codes, dictionary map might be safer but prefix logic is needed.
    # Let's use list comprehension for speed on the column.
    
    print("Applying 1:1 Mappings (Jeonbuk, Gunwi)...")
    agg_2023['source'] = agg_2023['source'].apply(map_code)
    agg_2023['target'] = agg_2023['target'].apply(map_code)
    
    # B. Split Bucheon (41190)
    # Identify rows to split
    mask_src_b = agg_2023['source'] == '41190'
    mask_tgt_b = agg_2023['target'] == '41190'
    
    # Separate Bucheon rows and Non-Bucheon rows
    df_b_src = agg_2023[mask_src_b].copy()
    df_b_tgt = agg_2023[mask_tgt_b].copy()
    
    # Note: A row could be source=41190 AND target=41190 (Intra-Bucheon)
    # But those were filtered out earlier. So these sets are disjoint for 'source!=target'.
    
    # Keep rows that DON'T involve Bucheon 41190
    df_preserved = agg_2023[~(mask_src_b | mask_tgt_b)].copy()
    
    print(f"Splitting {len(df_b_src)} source-Bucheon rows and {len(df_b_tgt)} target-Bucheon rows...")
    
    split_rows = []
    
    # Function to create split rows
    # We iterate through the Bucheon codes and their ratios
    # For each DataFrame (src or tgt), we create copies with modified codes/counts
    
    # 1. Split Source Bucheon (41190 -> 41192, 41194, 41196)
    if not df_b_src.empty:
        for b_code, ratio in bucheon_ratios.items():
            sub_df = df_b_src.copy()
            sub_df['source'] = b_code
            sub_df['count'] = (sub_df['count'] * ratio) # Keep float for now? No, round later?
            sub_df['hh_cnt'] = (sub_df['hh_cnt'] * ratio)
            sub_df['est'] = 1 # Mark as estimated
            split_rows.append(sub_df)

    # 2. Split Target Bucheon (41190 -> 41192, 41194, 41196)
    if not df_b_tgt.empty:
        for b_code, ratio in bucheon_ratios.items():
            sub_df = df_b_tgt.copy()
            sub_df['target'] = b_code
            sub_df['count'] = (sub_df['count'] * ratio)
            sub_df['hh_cnt'] = (sub_df['hh_cnt'] * ratio)
            sub_df['est'] = 1 # Mark as estimated
            split_rows.append(sub_df)
            
    # Combine
    if split_rows:
        df_split = pd.concat(split_rows)
        # Round counts to int
        df_split['count'] = df_split['count'].round().astype(int)
        df_split['hh_cnt'] = df_split['hh_cnt'].round().astype(int)
        
        # Combine with preserved rows
        agg_2023 = pd.concat([df_preserved, df_split], ignore_index=True)
    else:
        agg_2023 = df_preserved

    # Re-aggregate in case of duplicates created (unlikely with this logic unless...)
    # Actually, mapping 45->52 might merge distinct old rows if source/target overlap?
    # Unlikely as 1:1. But splitting Bucheon creates new specific rows.
    # Groupby again just to be safe and clean.
    # Also sum 'est' to keep it (if >0 then estimated)
    agg_2023['est'] = agg_2023.get('est', 0)
    agg_2023 = agg_2023.groupby(['source', 'target'])[['count', 'hh_cnt', 'est']].sum().reset_index()
    # Normalize est to 0 or 1
    agg_2023['est'] = agg_2023['est'].apply(lambda x: 1 if x > 0 else 0)
    
    print(f"2023 standardized records: {len(agg_2023)}")

    # 3. Merge and Calculate Diff
    print("Merging datasets...")
    # Left join on 2024 data
    merged = pd.merge(agg_2024, agg_2023, on=['source', 'target'], how='left', suffixes=('', '_prev'))
    
    # Fill NaN with 0 for counts
    merged['count'] = merged['count'].fillna(0).astype(int)
    merged['hh_cnt'] = merged['hh_cnt'].fillna(0).astype(int)
    merged['count_prev'] = merged['count_prev'].fillna(0).astype(int)
    # merged['est'] might be NaN if no match, fill with 0
    if 'est' in merged.columns:
        merged['est'] = merged['est'].fillna(0).astype(int)
    else:
        merged['est'] = 0
    
    # Calculate Diff
    merged['diff'] = merged['count'] - merged['count_prev']
    
    # 4. Build JSON Structure
    print("Building JSON structure...")
    result = {}
    
    for _, row in merged.iterrows():
        src = row['source']
        tgt = row['target']
        val = int(row['count'])
        diff = int(row['diff'])
        hh = int(row['hh_cnt'])
        est = int(row['est'])
        
        # Output structure
        data_packet = {'val': val, 'diff': diff, 'hh_cnt': hh}
        if est:
             data_packet['est'] = 1
        
        # 1. Outflow (Source -> Targets)
        if src not in result:
            result[src] = {'out': {}, 'in': {}}
        result[src]['out'][tgt] = data_packet
        
        # 2. Inflow (Target <- Sources)
        if tgt not in result:
            result[tgt] = {'out': {}, 'in': {}}
        result[tgt]['in'][src] = data_packet

    # 5. Generate Code Mapping (Census -> Admin) and Export
    print("Generating Code Mapping...")
    try:
        # 1. Read Admin Codes from Excel
        desc_path = os.path.join(DATA_DIR, "2024_description.xlsx")
        # Load Sheet 4 for Codes
        # Using header=None and skiprows=2 based on inspection
        # Col 3: Code (10 digit), Col 4: Name
        df_code = pd.read_excel(desc_path, sheet_name='전입·전출행정구역코드', header=None, skiprows=2)
        
        admin_map = {}
        for _, row in df_code.iterrows():
            raw_status = row[1] # Column B: Status
            raw_code = row[3]   # Column D: Code
            raw_name = row[4]   # Column E: Name
            malso_date = row[6] # Column G: Malso Date
            
            if pd.isna(raw_code) or pd.isna(raw_name):
                continue
                
            # Filter: Only Active codes
            # If Malso Date (Col 6) is NOT NaN, it is deleted.
            if not pd.isna(malso_date):
                 continue

            code_str = str(raw_code).strip()
            name_str = str(raw_name).strip()
            
            # Use first 5 digits as Sigungu Code
            if len(code_str) >= 5:
                sgg_code = code_str[:5]
                admin_map[name_str] = sgg_code

        # Manual Fix for Sejong City
        # GeoJSON says "세종특별자치시 세종시" (29010)
        # Data might have it as just "세종특별자치시" (36110)
        admin_map["세종특별자치시 세종시"] = "36110" 
        
        # Manual Fix for Pyeongtaek-si (User Request)
        # Force Pyeongtaek to 41220 even if logic found something else
        # '경기도 평택시' typically maps to 41220 (Active) but sometimes 41330 (Deleted) persists if not filtered.
        # With the filter above, it should be 41220, but adding explicit override for safety.
        admin_map["경기도 평택시"] = "41220"
        
        print(f"Admin Map Size: {len(admin_map)}")
        # print(f"Sample Admin Entry: {list(admin_map.items())[0]}")

        # 2. Read GeoJSON for Census Codes
        sigungu_path = 'dashboard/public/sigungu.json'
        with open(sigungu_path, 'r', encoding='utf-8') as f:
            geojson = json.load(f)

        code_mapping = {} # { "31570": "41820" }
        
        # Hardcoded Census Sido Code Map (for constructing name from GeoJSON)
        census_sido_map = {
            "11": "서울특별시", "21": "부산광역시", "22": "대구광역시", "23": "인천광역시", 
            "24": "광주광역시", "25": "대전광역시", "26": "울산광역시", "29": "세종특별자치시",
            "31": "경기도", "32": "강원특별자치도", "33": "충청북도", "34": "충청남도",
            "35": "전북특별자치도", "36": "전라남도", "37": "경상북도", "38": "경상남도",
            "39": "제주특별자치도"
        }
        
        # Update public/sido_mapping.json
        with open('dashboard/public/sido_mapping.json', 'w', encoding='utf-8') as f:
            json.dump(census_sido_map, f, ensure_ascii=False, indent=4)
        print("Updated sido_mapping.json for Census codes.")

        matched_count = 0
        
        print("Starting matching...")
        for feature in geojson['features']:
            props = feature['properties']
            c_code = props['SIGUNGU_CD'] 
            nm = props['SIGUNGU_NM']
            
            sido_c = c_code[:2]
            sido_nm = census_sido_map.get(sido_c, "")
            
            full_name = f"{sido_nm} {nm}".strip()
            
            if full_name in admin_map:
                code_mapping[c_code] = admin_map[full_name]
                matched_count += 1
            else:
                # Debug mismatch
                # print(f"Warning: No match for GeoJSON entry '{full_name}' ({c_code})")
                pass

        with open('dashboard/public/code_mapping.json', 'w', encoding='utf-8') as f:
            json.dump(code_mapping, f, indent=4)
        print(f"Generated code_mapping.json with {matched_count} matches.")

        # ---------------------------------------------------------
        # [NEW] Validation: Check for Missing Sigungu
        # ---------------------------------------------------------
        print("\n--- Validating Region Codes ---")
        missing_codes = []
        for feature in geojson['features']:
            c_code = feature['properties']['SIGUNGU_CD']
            c_name = feature['properties']['SIGUNGU_NM']
            sido_c = c_code[:2]
            sido_nm = census_sido_map.get(sido_c, "")
            full_name_g = f"{sido_nm} {c_name}".strip()

            # 1. Is it in Code Mapping?
            # If mapped, get the Admin Code. 
            if c_code not in code_mapping:
                missing_codes.append(f"{full_name_g} ({c_code})")

        if missing_codes:
            print(f"Warning: {len(missing_codes)} regions in GeoJSON are NOT mapped to Admin Codes:")
            for m in missing_codes[:20]: # Print top 20
                print(f" - {m}")
            if len(missing_codes) > 20:
                print(f" ... and {len(missing_codes)-20} more.")
        else:
            print("Success: All GeoJSON regions are mapped to Admin Codes.")
        print("-------------------------------\n")

    except Exception as e:
        print(f"Error generating mapping: {e}")
        import traceback
        traceback.print_exc()

    # 5. Export Data
    print(f"Exporting to {OUTPUT_FILE}...")
    output_dir = os.path.dirname(OUTPUT_FILE)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, separators=(',', ':')) # Minify
        
    print("Done!")
    # Print file size
    size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"Output file size: {size_mb:.2f} MB")

if __name__ == "__main__":
    process_od_data()
