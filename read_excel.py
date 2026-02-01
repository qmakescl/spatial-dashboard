
import pandas as pd
import sys

file_path = "datasets/popMove/houseHold/2024_description.xlsx"

try:
    # Read all sheets
    xls = pd.ExcelFile(file_path)
    print(f"Sheet names: {xls.sheet_names}")

    for sheet_name in xls.sheet_names:
        print(f"\n--- Sheet: {sheet_name} ---")
        df = pd.read_excel(xls, sheet_name=sheet_name)
        # Print the first few rows to understand structure
        print(df.to_markdown(index=False))
        # Also print detailed info if it looks like a metadata definition
        # (Usually first few rows are header/metadata, actual table starts later or is the whole thing)

except Exception as e:
    print(f"Error reading excel file: {e}")
