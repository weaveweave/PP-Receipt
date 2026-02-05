# Receipt Pipeline

Automated data extraction from PDF receipts to Excel spreadsheets using Vision LLM. This pipeline runs entirely on your local machine using LM Studio: All processing runs locally on your machine. Your receipt data never leaves your computer.

This project has been tested with multiple Vision LLM models (Qwen3-VL and olmOCR 2). You can switch between models to achieve different results based on your needs.

![Pipeline Overview](docs/images/pipeline-overview.png)

## Table of Contents

- [What It Does](#what-it-does)
- [Quick Start/Installing Guide](#quick-start)
  - [1. Install Dependencies](#1-install-dependencies)
  - [2. Install & Setup LM Studio](#2-install--setup-lm-studio)
  - [3. Add Your PDFs](#3-add-your-pdfs)
  - [4. Run Pipeline](#4-run-pipeline)
- [Extracted Fields](#extracted-fields)
  - [Customizing Fields for Different Receipt Types](#customizing-fields-for-different-receipt-types)
- [Requirements](#requirements)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Performance](#performance)
- [Screenshots](#screenshots)


## What It Does

Converts Indonesian receipt PDFs (kuitansi) into structured Excel files through three automated steps:

1. **PDF → Images** - Optimized preprocessing (grayscale, deskew, contrast enhancement)
2. **Images → JSON** - Data extraction via Vision LLM (LM Studio)
3. **JSON → Excel** - Formatted spreadsheet generation

![Sample Output](docs/images/sample-output.png)

## Quick Start

### 1. Install Dependencies

```bash
chmod +x setup.sh
./setup.sh
```


### 2. Install & Setup LM Studio

**Download LM Studio:**
1. Go to https://lmstudio.ai
2. Download for macOS (Apple Silicon)
3. Install like any macOS app (drag to Applications)

**Download Model:**
1. Open LM Studio
2. Click **"Search"** tab (🔍 icon on left sidebar)
3. Search for: `qwen3-vl`
4. Click **Download** on "Qwen3-VL" model (choose Q4 or Q5 quantization)
5. Wait for download to complete (~2-3GB)

![LM Studio Model Download](docs/images/lm-studio-download.png)

**Start Server:**
1. Click **"Local Server"** tab (📡 icon on left sidebar)
2. In "Select model to load" dropdown, choose **Qwen3-VL**
3. Click **"Start Server"** button
4. Keep LM Studio running while using the pipeline

![LM Studio Server](docs/images/lm-studio-server.png)


### 3. Add Your PDFs

Place PDF receipt files in the `input_pdfs/` folder.


### 4. Run Pipeline

**Run all steps:**
```bash
python3 run_pipeline.py
```

**Or run individual steps:**
```bash
# Step 1 only: PDF to Images
python3 step1_pdf_to_images.py

# Step 2 only: Images to JSON (requires Step 1 output)
python3 step2_extract_data.py

# Step 3 only: JSON to Excel (requires Step 2 output)
python3 step3_json_to_excel.py
```

**Output:** `output/step3_excel/Rekapitulasi_Kuitansi.xlsx`


## Extracted Fields

This project is configured to extract the following fields from Indonesian kuitansi receipts:

| Field | Description |
|-------|-------------|
| `no_kuitansi` | Receipt number |
| `tanggal` | Date (DD-MM-YYYY) |
| `penerima` | Recipient name |
| `uang_sejumlah_rp` | Amount in Rupiah |
| `jumlah_liter` | Volume in Liters |
| `keterangan` | Notes/percentage |


### Customizing Fields for Different Receipt Types

To adapt this pipeline for other receipt formats:

**1. Modify the extraction prompt in `config.py`:**

Find the `EXTRACTION_PROMPT` variable and update field descriptions:

```python
EXTRACTION_PROMPT = """
# Modify this section to match your receipt format
1. **field_name**: Description of where to find this field
2. **another_field**: Location on your receipt
...
"""
```

**2. Update the field list in `config.py`:**

Change `EXCEL_COLUMNS` to match your new fields:

```python
EXCEL_COLUMNS = [
    "Field 1 Name",
    "Field 2 Name",
    "Field 3 Name",
    # Add or remove fields as needed
]
```

**3. Update sanitization logic in `step2_extract_data.py`:**

Modify the `sanitize_extracted_data()` function if your fields need special formatting (e.g., different number formats, date formats, etc.)


## Requirements

- Python 3.9+
- macOS (Apple Silicon optimized)
- 8-16GB RAM
- LM Studio with Qwen3-VL model (or OLMoCR2)

**Optional Models:**
- **OLMoCR2** - Alternative vision model with good OCR performance
- **Ministral-3** - Faster but less accurate


## Configuration

Edit `config.py` to customize:

```python
# Model selection
LM_STUDIO_MODEL = "qwen3-vl"     # Default (recommended)
# LM_STUDIO_MODEL = "olmocr-2"   # Alternative (uncomment to use)

# Image quality
PDF_TO_IMAGE_DPI = 300            # Higher = better quality, larger files

# Parallel processing
MAX_WORKERS_CAP = 6               # Adjust based on RAM (2-6)

# Preprocessing options
ENABLE_DESKEW = True              # Auto-rotate skewed images
ENABLE_NOISE_REDUCTION = True     # Remove scan noise
ENABLE_CONTRAST_ENHANCEMENT = True # Improve text clarity
```

**To use OLMoCR2 model:**
1. Download OLMoCR2 in LM Studio (search "olmocr-2")
2. In `config.py`, change:
   ```python
   LM_STUDIO_MODEL = "olmocr-2"
   ```
3. Restart the pipeline



## Project Structure

```
receipt-pipeline/
├── config.py                    # Configuration
├── step1_pdf_to_images.py       # PDF preprocessing
├── step2_extract_data.py        # Data extraction
├── step3_json_to_excel.py       # Excel generation
├── run_pipeline.py              # Run all steps
├── test_setup.py                # Verify setup
├── setup.sh                     # Install dependencies
├── requirements.txt             # Python packages
├── input_pdfs/                  # Input folder
└── output/                      # Output folders
    ├── step1_images/            # Preprocessed images
    ├── step2_json/              # Extracted data
    └── step3_excel/             # Final Excel files
```


## Troubleshooting

**Can't connect to LM Studio**
- Ensure LM Studio is running
- Verify server is started on port 1234
- Check that model is loaded in "Local Server" tab

**Low extraction accuracy**
- Use Qwen3-VL model (most accurate)
- Verify PDF quality (not too blurry)
- Increase `PDF_TO_IMAGE_DPI` to 400 in config.py

**Out of memory errors**
- Reduce `MAX_WORKERS_CAP` to 3 in config.py
- Close other applications
- Process fewer PDFs at once

**Wrong field extracted**
- Check PDF format matches extraction prompt
- Modify `EXTRACTION_PROMPT` in config.py
- See "Customizing Fields" section above


## Performance

MacBook M2 16GB:
- Speed: 4-6 receipts/minute
- Accuracy: 95%+ with Qwen3-VL
- 50 receipts in ~10 minutes


## Screenshots

### Pipeline in Action

![Pipeline Running](docs/images/pipeline-running.png)

### Excel Output Example

![Excel Output](docs/images/excel-output.png)

### LM Studio Setup

![LM Studio Configuration](docs/images/lm-studio-config.png)


## Version

2.0 - February 2026
