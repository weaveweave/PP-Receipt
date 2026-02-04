#!/usr/bin/env python3
"""
Test script to verify receipt pipeline setup
Checks all dependencies and configurations
"""

import sys
import os

def print_status(check_name, status, message=""):
    """Print colored status message"""
    if status:
        print(f"âœ… {check_name}: OK {message}")
    else:
        print(f"âŒ {check_name}: FAILED {message}")
    return status

def check_python_version():
    """Check if Python version is 3.9 or higher"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        return print_status("Python version", True, f"({version.major}.{version.minor}.{version.micro})")
    else:
        return print_status("Python version", False, f"({version.major}.{version.minor} - need 3.9+)")

def check_imports():
    """Check if all required packages can be imported"""
    packages = [
        ("OpenCV", "cv2"),
        ("Pillow", "PIL"),
        ("pdf2image", "pdf2image"),
        ("openpyxl", "openpyxl"),
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("requests", "requests"),
        ("psutil", "psutil"),
    ]
    
    all_ok = True
    for name, module in packages:
        try:
            __import__(module)
            print_status(f"Package: {name}", True)
        except ImportError as e:
            print_status(f"Package: {name}", False, f"({e})")
            all_ok = False
    
    return all_ok

def check_poppler():
    """Check if poppler is installed (for pdf2image)"""
    try:
        from pdf2image import convert_from_path
        # Try to use pdfinfo (part of poppler)
        import subprocess
        result = subprocess.run(['pdfinfo', '-v'], capture_output=True, text=True)
        if result.returncode == 0:
            return print_status("Poppler", True)
        else:
            return print_status("Poppler", False, "(pdfinfo not found)")
    except Exception as e:
        return print_status("Poppler", False, f"({e})")

def check_directories():
    """Check if required directories exist"""
    dirs = [
        "input_pdfs",
        "output",
        "output/step1_images",
        "output/step2_json",
        "output/step3_excel",
    ]
    
    all_ok = True
    for dir_path in dirs:
        exists = os.path.exists(dir_path)
        if not exists:
            all_ok = False
        print_status(f"Directory: {dir_path}", exists)
    
    return all_ok

def check_config():
    """Check if config.py exists and can be imported"""
    try:
        import config
        print_status("config.py", True)
        print(f"   - LM Studio URL: {config.LM_STUDIO_BASE_URL}")
        print(f"   - Model: {config.LM_STUDIO_MODEL}")
        print(f"   - DPI: {config.PDF_TO_IMAGE_DPI}")
        return True
    except Exception as e:
        return print_status("config.py", False, f"({e})")

def check_lm_studio():
    """Check if LM Studio server is accessible"""
    try:
        import requests
        import config
        
        response = requests.get(f"{config.LM_STUDIO_BASE_URL}/v1/models", timeout=2)
        if response.status_code == 200:
            print_status("LM Studio server", True, f"(running on {config.LM_STUDIO_BASE_URL})")
            
            # Try to get model info
            models = response.json()
            if 'data' in models and len(models['data']) > 0:
                loaded_model = models['data'][0].get('id', 'unknown')
                print(f"   - Loaded model: {loaded_model}")
            
            return True
        else:
            return print_status("LM Studio server", False, f"(HTTP {response.status_code})")
    except requests.exceptions.ConnectionError:
        return print_status("LM Studio server", False, "(not running - start it in LM Studio)")
    except Exception as e:
        return print_status("LM Studio server", False, f"({e})")

def check_sample_pdfs():
    """Check if there are sample PDFs to process"""
    if not os.path.exists("input_pdfs"):
        return print_status("Sample PDFs", False, "(input_pdfs directory not found)")
    
    pdf_files = [f for f in os.listdir("input_pdfs") if f.endswith('.pdf')]
    
    if len(pdf_files) > 0:
        return print_status("Sample PDFs", True, f"({len(pdf_files)} PDF(s) found)")
    else:
        return print_status("Sample PDFs", False, "(no PDFs in input_pdfs/ - add some to test)")

def main():
    """Run all checks"""
    
    print("=" * 60)
    print("  Receipt Pipeline - Setup Verification")
    print("=" * 60)
    print()
    
    results = []
    
    print("ðŸ“‹ Checking Python...")
    results.append(check_python_version())
    print()
    
    print("ðŸ“¦ Checking Python packages...")
    results.append(check_imports())
    print()
    
    print("ðŸ”§ Checking system tools...")
    results.append(check_poppler())
    print()
    
    print("ðŸ“ Checking directories...")
    results.append(check_directories())
    print()
    
    print("âš™ï¸  Checking configuration...")
    results.append(check_config())
    print()
    
    print("ðŸ¤– Checking LM Studio...")
    lm_studio_ok = check_lm_studio()
    print()
    
    print("ðŸ“„ Checking input files...")
    has_pdfs = check_sample_pdfs()
    print()
    
    # Summary
    print("=" * 60)
    print("  Summary")
    print("=" * 60)
    
    required_checks = sum(results)
    total_required = len(results)
    
    if all(results):
        print("âœ… All required checks passed!")
        print()
        
        if lm_studio_ok:
            print("âœ… LM Studio is ready")
        else:
            print("âš ï¸  LM Studio not running - start it before running Step 2")
        
        if has_pdfs:
            print("âœ… PDFs ready to process")
        else:
            print("âš ï¸  No PDFs found - add some to input_pdfs/ to test")
        
        print()
        print("ðŸŽ‰ Setup verified! You can run the pipeline:")
        print("   python3 run_pipeline.py")
    else:
        print(f"âŒ Some checks failed ({required_checks}/{total_required} passed)")
        print()
        print("Please fix the failed checks before running the pipeline.")
        print("See README.md for installation instructions.")
        sys.exit(1)
    
    print()

if __name__ == "__main__":
    main()
