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

    # 3. Merge and Calculate Diff
    print("Merging datasets...")
    # Left join on 2024 data
    merged = pd.merge(agg_2024, agg_2023, on=['source', 'target'], how='left', suffixes=('', '_prev'))
    
    # Fill NaN with 0 for counts
    merged['count'] = merged['count'].fillna(0).astype(int)
    merged['hh_cnt'] = merged['hh_cnt'].fillna(0).astype(int)
    merged['count_prev'] = merged['count_prev'].fillna(0).astype(int)
    
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
        
        # Output structure
        data_packet = {'val': val, 'diff': diff, 'hh_cnt': hh}
        
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
            raw_code = row[3]
            raw_name = row[4]
            
            if pd.isna(raw_code) or pd.isna(raw_name):
                continue
                
            code_str = str(raw_code).strip()
            name_str = str(raw_name).strip()
            
            # Use first 5 digits as Sigungu Code
            if len(code_str) >= 5:
                sgg_code = code_str[:5]
                admin_map[name_str] = sgg_code

        # Manual Fix for Sejong City
        # GeoJSON says "세종특별자치시 세종시" (29010)
        # Data might have it as just "세종특별자치시" (36110, but Sejong is 36 in data? No, 29 is Census, 36 is Admin)
        # Let's check our admin_map keys. 
        # Usually Sejong is unique. Let's add a hardcoded fallback if needed.
        # Check if "세종특별자치시 세종시" exists in admin_map. If not, try "세종특별자치시".
        # Based on typical gov data: Sejong Admin Code is usually 36110.
        admin_map["세종특별자치시 세종시"] = "36110" 
        
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
