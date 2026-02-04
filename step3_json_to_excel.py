"""
Step 3: Convert extracted JSON data to Excel spreadsheet
Creates a nicely formatted Excel file with all receipt data
"""

import os
import json
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, Border, Side, Alignment, PatternFill

from config import (
    STEP2_OUTPUT_DIR,
    STEP3_OUTPUT_DIR,
    EXCEL_OUTPUT_FILENAME,
    EXCEL_SHEET_NAME,
    EXCEL_COLUMNS,
    EXCEL_AUTO_WIDTH,
    EXCEL_FREEZE_HEADER,
    EXCEL_ADD_BORDERS,
    EXCEL_HEADER_BOLD,
    VERBOSE
)


# ============================================================================
# JSON LOADING
# ============================================================================

def load_all_json_files(json_dir):
    """
    Load all JSON files from directory
    
    Args:
        json_dir (str): Directory containing JSON files
    
    Returns:
        list: List of dictionaries with extracted data
    """
    
    json_files = [
        os.path.join(json_dir, f)
        for f in os.listdir(json_dir)
        if f.endswith('.json')
    ]
    
    if not json_files:
        print("âš ï¸  No JSON files found!")
        return []
    
    print(f"ðŸ“Š Found {len(json_files)} JSON file(s)")
    
    all_data = []
    errors = []
    
    for json_path in sorted(json_files):
        filename = Path(json_path).name
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_data.append(data)
                if VERBOSE:
                    print(f"  âœ“ Loaded: {filename}")
        except Exception as e:
            errors.append({"file": filename, "error": str(e)})
            print(f"  âœ— Error loading {filename}: {e}")
    
    print(f"âœ… Successfully loaded {len(all_data)} file(s)")
    
    if errors:
        print(f"âš ï¸  Failed to load {len(errors)} file(s)")
    
    return all_data


# ============================================================================
# DATA TRANSFORMATION
# ============================================================================

def transform_to_dataframe(data_list):
    """
    Transform list of JSON data to pandas DataFrame
    
    Args:
        data_list (list): List of dictionaries
    
    Returns:
        pd.DataFrame: DataFrame with standardized columns
    """
    
    if not data_list:
        print("âš ï¸  No data to transform!")
        return pd.DataFrame()
    
    # Create DataFrame
    df = pd.DataFrame(data_list)
    
    # Ensure all required columns exist
    required_fields = ["no_kuitansi", "tanggal", "penerima", "uang_sejumlah_rp", "jumlah_liter", "keterangan"]
    for field in required_fields:
        if field not in df.columns:
            df[field] = ""
    
    # Reorder columns to match EXCEL_COLUMNS
    df = df[required_fields]
    
    # Rename columns to display names
    df.columns = EXCEL_COLUMNS
    
    # Format currency column (add thousands separator)
    currency_col = "Uang Sejumlah (Rp)"
    if currency_col in df.columns:
        df[currency_col] = df[currency_col].apply(lambda x: format_currency(x))
    
    # Sort by No. Kuitansi
    if "No. Kuitansi" in df.columns:
        # Convert to numeric for proper sorting
        df["No. Kuitansi"] = pd.to_numeric(df["No. Kuitansi"], errors='coerce')
        df = df.sort_values("No. Kuitansi")
        # Convert back to string
        df["No. Kuitansi"] = df["No. Kuitansi"].fillna("").astype(str).str.replace(".0", "", regex=False)
    
    print(f"ðŸ“Š Created DataFrame with {len(df)} rows")
    
    return df


def format_currency(value):
    """
    Format currency value with thousands separator
    
    Args:
        value: Currency value (string or number)
    
    Returns:
        str: Formatted currency string
    """
    
    if not value or value == "":
        return ""
    
    try:
        # Convert to integer
        num = int(str(value).replace(",", "").replace(".", ""))
        # Format with thousands separator
        return f"{num:,}".replace(",", ".")
    except:
        return str(value)


# ============================================================================
# EXCEL FORMATTING
# ============================================================================

def apply_excel_formatting(excel_path):
    """
    Apply formatting to Excel file: bold headers, borders, auto-width, etc.
    
    Args:
        excel_path (str): Path to Excel file
    """
    
    print("ðŸŽ¨ Applying Excel formatting...")
    
    # Load workbook
    wb = load_workbook(excel_path)
    ws = wb.active
    
    # Define styles
    header_font = Font(bold=True, size=11)
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    center_alignment = Alignment(horizontal='center', vertical='center')
    left_alignment = Alignment(horizontal='left', vertical='center')
    
    # Apply header formatting
    if EXCEL_HEADER_BOLD:
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment
            if EXCEL_ADD_BORDERS:
                cell.border = thin_border
    
    # Apply borders to all cells
    if EXCEL_ADD_BORDERS:
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=ws.max_column):
            for cell in row:
                cell.border = thin_border
                # Center-align numeric columns
                if cell.column in [1, 4, 5]:  # No. Kuitansi, Uang Sejumlah, Jumlah Liter
                    cell.alignment = center_alignment
                else:
                    cell.alignment = left_alignment
    
    # Auto-adjust column widths
    if EXCEL_AUTO_WIDTH:
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            
            for cell in column:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            
            # Set width with some padding
            adjusted_width = min(max_length + 2, 50)  # Cap at 50
            ws.column_dimensions[column_letter].width = adjusted_width
    
    # Freeze header row
    if EXCEL_FREEZE_HEADER:
        ws.freeze_panes = "A2"
    
    # Save workbook
    wb.save(excel_path)
    print("âœ… Formatting applied")


# ============================================================================
# EXCEL GENERATION
# ============================================================================

def create_excel(data_list, output_path):
    """
    Create Excel file from JSON data
    
    Args:
        data_list (list): List of dictionaries with receipt data
        output_path (str): Path to save Excel file
    
    Returns:
        bool: True if successful, False otherwise
    """
    
    if not data_list:
        print("âŒ No data to create Excel file!")
        return False
    
    try:
        # Transform to DataFrame
        df = transform_to_dataframe(data_list)
        
        if df.empty:
            print("âŒ DataFrame is empty!")
            return False
        
        # Save to Excel
        print(f"ðŸ’¾ Saving to Excel: {output_path}")
        df.to_excel(output_path, sheet_name=EXCEL_SHEET_NAME, index=False, engine='openpyxl')
        
        # Apply formatting
        apply_excel_formatting(output_path)
        
        print(f"âœ… Excel file created successfully!")
        print(f"   - Rows: {len(df)}")
        print(f"   - Columns: {len(df.columns)}")
        
        return True
    
    except Exception as e:
        print(f"âŒ Error creating Excel file: {e}")
        return False


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""
    
    print("=" * 60)
    print("ðŸš€ STEP 3: CONVERT JSON TO EXCEL")
    print("=" * 60)
    print(f"Input directory: {STEP2_OUTPUT_DIR}")
    print(f"Output directory: {STEP3_OUTPUT_DIR}")
    print(f"Output filename: {EXCEL_OUTPUT_FILENAME}")
    
    # Check if input directory exists
    if not os.path.exists(STEP2_OUTPUT_DIR):
        print(f"\nâŒ Error: Input directory not found: {STEP2_OUTPUT_DIR}")
        print("   Please run step2_extract_data.py first")
        return
    
    # Load all JSON files
    print(f"\nðŸ“‚ Loading JSON files from {STEP2_OUTPUT_DIR}...")
    data_list = load_all_json_files(STEP2_OUTPUT_DIR)
    
    if not data_list:
        print("\nâŒ No data found to process!")
        return
    
    # Create output directory
    os.makedirs(STEP3_OUTPUT_DIR, exist_ok=True)
    
    # Create Excel file
    output_path = os.path.join(STEP3_OUTPUT_DIR, EXCEL_OUTPUT_FILENAME)
    print(f"\nðŸ“Š Creating Excel spreadsheet...")
    
    success = create_excel(data_list, output_path)
    
    if success:
        print("\nâœ¨ Step 3 completed!")
        print(f"ðŸ“ Output saved to: {output_path}")
        print(f"\nðŸŽ‰ Pipeline completed successfully!")
        print(f"   You can now open the Excel file to view all extracted receipt data.")
    else:
        print("\nâŒ Failed to create Excel file")


if __name__ == "__main__":
    main()
