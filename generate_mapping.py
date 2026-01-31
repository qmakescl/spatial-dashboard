import pandas as pd
import json
import os

# File paths
excel_path = 'datasets/spatial/sigungu/센서스 공간정보 지역 코드.xlsx'
output_path = 'export/spatial/sido_mapping.json'

def generate_sido_mapping():
    print(f"Loading Excel file from: {excel_path}")
    
    # Check if file exists
    if not os.path.exists(excel_path):
        print(f"Error: File not found at {excel_path}")
        return

    try:
        # Load the Excel file. Assuming the sheet name is "2024년 6월" based on previous context,
        # but let's try to load the first sheet if that fails or just load the file to inspect sheets.
        # Since the user mentioned "2024년 6월" sheet in the instruction file, we'll try that first.
        # However, to be robust, let's load the excel file and check sheet names.
        xls = pd.ExcelFile(excel_path)
        sheet_name = "2024년 6월"
        
        if sheet_name not in xls.sheet_names:
            print(f"Sheet '{sheet_name}' not found. Available sheets: {xls.sheet_names}")
            # Fallback to the first sheet if specific sheet not found
            sheet_name = xls.sheet_names[0]
            print(f"Using sheet: {sheet_name}")

        df = pd.read_excel(xls, sheet_name=sheet_name, header=1)
        
        # Display first few rows to understand structure
        print("First 5 rows of the dataframe:")
        print(df.head())
        print("-" * 30)

        # Expected columns: 시도코드, 시도명 (based on typical structure, but need to verify)
        # Let's find columns that look like code and name
        # Usually it's something like '시도코드', '시도명'
        
        # Clean column names (remove spaces)
        df.columns = df.columns.astype(str).str.strip()
        
        print(f"Columns: {df.columns.tolist()}")
        
        sido_code_col = None
        sido_name_col = None
        
        for col in df.columns:
            if '시도코드' in col:
                sido_code_col = col
            elif '시도명' in col:
                sido_name_col = col
        
        if not sido_code_col or not sido_name_col:
            print("Could not identify Sido Code or Name columns automatically.")
            print("Please check the column names printed above.")
            return

        print(f"Using columns: Code='{sido_code_col}', Name='{sido_name_col}'")

        # Extract unique Sido code and name pairs
        sido_df = df[[sido_code_col, sido_name_col]].drop_duplicates().sort_values(by=sido_code_col)
        
        # Create dictionary
        sido_mapping = {}
        for _, row in sido_df.iterrows():
            code = str(row[sido_code_col]).zfill(2) # Ensure 2 digits
            name = str(row[sido_name_col]).strip()
            sido_mapping[code] = name
            
        print(f"Found {len(sido_mapping)} Sido entries.")
        print(sido_mapping)
        
        # Save to JSON
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sido_mapping, f, ensure_ascii=False, indent=2)
            
        print(f"Successfully saved mapping to {output_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    generate_sido_mapping()
