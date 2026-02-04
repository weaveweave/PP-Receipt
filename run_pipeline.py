#!/usr/bin/env python3
"""
Run complete receipt extraction pipeline
Executes all 3 steps sequentially: PDF → Images → JSON → Excel
"""

import sys
import time
from datetime import datetime

# Import all steps
import step1_pdf_to_images
import step2_extract_data
import step3_json_to_excel


def print_banner(text):
    """Print a formatted banner"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def run_complete_pipeline():
    """Run all three steps of the pipeline"""
    
    start_time = time.time()
    
    print_banner("🚀 RECEIPT EXTRACTION PIPELINE - FULL RUN")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 1: PDF to Images
        print_banner("STEP 1: PDF → OPTIMIZED IMAGES")
        step1_pdf_to_images.main()
        
        # Step 2: Images to JSON
        print_banner("STEP 2: IMAGES → JSON DATA")
        step2_extract_data.main()
        
        # Step 3: JSON to Excel
        print_banner("STEP 3: JSON → EXCEL SPREADSHEET")
        step3_json_to_excel.main()
        
        # Summary
        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        
        print_banner("✨ PIPELINE COMPLETED SUCCESSFULLY!")
        print(f"Total time: {minutes} minutes {seconds} seconds")
        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n🎉 All done! Check the output folder for your Excel file.\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Pipeline failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_complete_pipeline()
