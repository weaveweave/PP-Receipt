# Receipt Pipeline - Windows Setup Guide

**Complete step-by-step guide to run this project on Windows 10/11**

---

## Prerequisites

- Windows 10 or Windows 11
- At least 8GB RAM (16GB recommended)
- 10GB free disk space
- Administrator access

---

## Step 1: Install Python

### 1.1 Download Python

1. Go to https://www.python.org/downloads/
2. Click **"Download Python 3.11.x"** (or latest 3.9+)
3. Run the downloaded installer

### 1.2 Install Python

**IMPORTANT:** During installation:
- ✅ **Check "Add Python to PATH"** (very important!)
- ✅ Check "Install pip"
- Click **"Install Now"**

### 1.3 Verify Installation

1. Open **Command Prompt** (press `Win + R`, type `cmd`, press Enter)
2. Type:
   ```cmd
   python --version
   ```
3. Should show: `Python 3.11.x` or similar
4. Type:
   ```cmd
   pip --version
   ```
5. Should show pip version

**If "python" is not recognized:**
- Restart your computer
- Or manually add Python to PATH (see Troubleshooting section)

---

## Step 2: Install Poppler (PDF Processing Tool)

### 2.1 Download Poppler

1. Go to: https://github.com/oschwartz10612/poppler-windows/releases
2. Download **Latest release** (example: `Release-XX.XX.X-0.zip`)
3. Extract the ZIP file to `C:\poppler`

Your folder structure should look like:
```
C:\poppler\
├── Library\
├── bin\          ← This folder contains pdfinfo.exe, pdftoppm.exe, etc.
└── ...
```

### 2.2 Add Poppler to PATH

1. Press `Win + R`, type `sysdm.cpl`, press Enter
2. Click **"Advanced"** tab
3. Click **"Environment Variables"**
4. Under **"System variables"**, find **"Path"**, click **"Edit"**
5. Click **"New"**
6. Add: `C:\poppler\Library\bin`
7. Click **"OK"** on all windows
8. **Restart Command Prompt**

### 2.3 Verify Poppler

Open a **new** Command Prompt and type:
```cmd
pdfinfo -v
```

Should show Poppler version. If it says "not recognized", check the PATH setup again.

---

## Step 3: Download the Project

### Option A: Download ZIP (Easier)

1. Download the project ZIP file
2. Extract to a folder like `C:\receipt-pipeline`
3. Open Command Prompt in that folder:
   - Navigate: `cd C:\receipt-pipeline`

### Option B: Using Git

1. Install Git: https://git-scm.com/download/win
2. Open Command Prompt
3. Run:
   ```cmd
   git clone [repository-url]
   cd receipt-pipeline
   ```

---

## Step 4: Install Python Dependencies

1. Open Command Prompt in the project folder
2. Run:
   ```cmd
   pip install -r requirements.txt
   ```

This will install:
- PyPDF2, pdf2image (PDF processing)
- opencv-python, Pillow (image processing)
- pandas, openpyxl (Excel)
- requests (API calls)

**Wait for installation to complete** (may take 2-5 minutes)

---

## Step 5: Install LM Studio

### 5.1 Download LM Studio

1. Go to: https://lmstudio.ai
2. Click **"Download for Windows"**
3. Run the installer (`.exe` file)
4. Follow installation wizard

### 5.2 Download Vision Model

1. **Open LM Studio**
2. Click **"Search"** (🔍 icon on left sidebar)
3. In search box, type: `qwen3-vl`
4. Click **"Download"**
   - Choose **Q4** or **Q5** quantization (smaller = faster, less accurate)
   - Wait for download (~2-3GB)

**Alternative models** (if Qwen3-VL doesn't work):
- Search for: `olmocr-2` or `ministral-3`

### 5.3 Start LM Studio Server

1. In LM Studio, click **"Local Server"** tab
2. In **"Select model to load"** dropdown, choose your downloaded model
3. Click **"Start Server"** button
4. **Keep LM Studio running** while using the pipeline

You should see: "Server started on http://localhost:1234"

---

## Step 6: Create Directory Structure

Open Command Prompt in the project folder and run:

```cmd
mkdir input_pdfs
mkdir output
mkdir output\step1_images
mkdir output\step2_json
mkdir output\step3_excel
```

---

## Step 7: Verify Setup

Run the test script:

```cmd
python test_setup.py
```

You should see checkmarks (✓) for:
- ✓ Python version
- ✓ All packages
- ✓ Poppler
- ✓ Directories
- ✓ config.py
- ✓ LM Studio server (if running)

**If any checks fail**, see the Troubleshooting section below.

---

## Step 8: Add Your PDF Files

1. Copy your receipt PDF files to the `input_pdfs\` folder
2. Example:
   ```
   input_pdfs\
   ├── receipt1.pdf
   ├── receipt2.pdf
   └── receipt3.pdf
   ```

---

## Step 9: Run the Pipeline

### Option A: Run Complete Pipeline (Recommended)

```cmd
python run_pipeline.py
```

This runs all 3 steps automatically.

### Option B: Run Steps Individually

**Step 1 only:** (PDF → Images)
```cmd
python step1_pdf_to_images.py
```

**Step 2 only:** (Images → JSON)
```cmd
python step2_extract_data.py
```

**Step 3 only:** (JSON → Excel)
```cmd
python step3_json_to_excel.py
```

---

## Step 10: Get Your Results

After the pipeline completes:

1. Open: `output\step3_excel\Rekapitulasi_Kuitansi.xlsx`
2. Your extracted receipt data is ready!

---

## Common Issues & Troubleshooting

### Issue 1: "python is not recognized"

**Solution:**
1. Uninstall Python
2. Reinstall and **check "Add Python to PATH"**
3. Or manually add to PATH:
   - Find Python folder (usually `C:\Users\YourName\AppData\Local\Programs\Python\Python311`)
   - Add to System PATH (see Step 2.2 instructions)

### Issue 2: "pdfinfo is not recognized"

**Solution:**
1. Check Poppler is in `C:\poppler\Library\bin`
2. Verify PATH includes `C:\poppler\Library\bin`
3. Restart Command Prompt
4. If still fails, add the **full path** to bin folder

### Issue 3: "Cannot connect to LM Studio"

**Solution:**
1. Make sure LM Studio is running
2. Check that server is started (green indicator)
3. Verify URL is `http://localhost:1234` in LM Studio settings
4. Try restarting LM Studio

### Issue 4: "Failed to install opencv-python"

**Solution:**
1. Install Visual C++ Redistributable:
   - Download: https://aka.ms/vs/17/release/vc_redist.x64.exe
   - Run installer
2. Retry: `pip install opencv-python`

### Issue 5: "Out of memory" errors

**Solution:**
1. Edit `config.py`
2. Change `MAX_WORKERS_CAP = 6` to `MAX_WORKERS_CAP = 2`
3. Change `RAM_PER_WORKER = 2.0` to `RAM_PER_WORKER = 3.0`

### Issue 6: Low extraction accuracy

**Solution:**
1. Try different model (OLMoCR2 instead of Qwen3-VL)
2. Increase image quality in `config.py`:
   - Change `PDF_TO_IMAGE_DPI = 300` to `PDF_TO_IMAGE_DPI = 400`
3. Make sure PDFs are not too blurry

### Issue 7: "ModuleNotFoundError: No module named 'config'"

**Solution:**
- You need a `config.py` file in the project folder
- This file is missing from the uploaded documents
- You'll need to create it or get it from the original project

---

## Windows-Specific Notes

### File Paths
- Use backslash `\` in Windows paths
- Example: `C:\receipt-pipeline\input_pdfs`

### Permissions
- If you get "Permission denied" errors, run Command Prompt as Administrator:
  - Right-click Command Prompt → "Run as administrator"

### Antivirus
- Some antivirus software may block Python scripts
- Add project folder to antivirus exceptions if needed

---

## Configuration (Optional)

Edit `config.py` to customize:

### Change Model
```python
# Use different model
LM_STUDIO_MODEL = "olmocr-2"  # Instead of qwen3-vl
```

### Adjust Image Quality
```python
# Higher DPI = better quality, slower processing
PDF_TO_IMAGE_DPI = 400  # Default: 300
```

### Reduce Memory Usage
```python
# For 8GB RAM systems
MAX_WORKERS_CAP = 2      # Default: 6
RAM_PER_WORKER = 3.0     # Default: 2.0
```

### Disable Preprocessing Steps
```python
# Skip certain steps if they cause issues
ENABLE_DESKEW = False              # Skip rotation correction
ENABLE_NOISE_REDUCTION = False     # Skip denoising
ENABLE_CONTRAST_ENHANCEMENT = True # Keep contrast (recommended)
```

---

## Uninstalling

To remove everything:

1. **Delete project folder**
2. **Uninstall Python** (optional):
   - Settings → Apps → Python → Uninstall
   - Remove from PATH
3. **Remove Poppler** (optional):
   - Delete `C:\poppler`
   - Remove from PATH
4. **Uninstall LM Studio** (optional):
   - Settings → Apps → LM Studio → Uninstall

---

## Getting Help

If you encounter issues:

1. Run `python test_setup.py` to diagnose
2. Check error messages carefully
3. Verify all installation steps were completed
4. Make sure LM Studio server is running
5. Try with a single, clear PDF first

---

## Next Steps

Once everything is working:

1. **Process your receipts** in batches
2. **Customize fields** if needed (edit prompts in config.py)
3. **Try different models** to improve accuracy
4. **Adjust preprocessing** for your specific receipt types

**Estimated total setup time:** 20-30 minutes
