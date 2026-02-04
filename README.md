# Receipt Pipeline

Automated data extraction from PDF receipts to Excel spreadsheets using Vision LLM (tested with Qwen3-VL and olmOCR 2).

## What It Does

Converts Indonesian receipt PDFs (kuitansi) into structured Excel files through three automated steps:

1. **PDF → Images** - Optimized preprocessing (grayscale, deskew, contrast enhancement)
2. **Images → JSON** - Data extraction via Vision LLM (LM Studio)
3. **JSON → Excel** - Formatted spreadsheet generation

## Quick Start

```bash
# 1. Install dependencies
./setup.sh

# 2. Install LM Studio from lmstudio.ai
#    Download Qwen3-VL model
#    Start server on port 1234

# 3. Add PDFs to input_pdfs/ folder

# 4. Run pipeline
python3 run_pipeline.py
```

Output: `output/step3_excel/Rekapitulasi_Kuitansi.xlsx`

## Extracted Fields

- Receipt number
- Date
- Recipient name
- Amount (Rupiah)
- Volume (Liters)
- Notes/percentage

## Requirements

- Python 3.9+
- macOS (Apple Silicon optimized)
- 8-16GB RAM
- LM Studio with Qwen3-VL model

## Configuration

Edit `config.py` to customize:

```python
LM_STUDIO_MODEL = "qwen3-vl"     # Change model
PDF_TO_IMAGE_DPI = 300            # Image quality
MAX_WORKERS_CAP = 6               # Parallel processing
```

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
    ├── step1_images/
    ├── step2_json/
    └── step3_excel/
```

## Troubleshooting

**Can't connect to LM Studio**
- Ensure LM Studio is running
- Verify server started on port 1234
- Check model is loaded

**Low accuracy**
- Use Qwen3-VL model
- Check PDF quality
- Increase `PDF_TO_IMAGE_DPI`

**Out of memory**
- Reduce `MAX_WORKERS_CAP` to 3
- Close other applications

## Performance

MacBook M2 16GB:
- Speed: 4-6 receipts/minute
- Accuracy: 95%+ with Qwen3-VL
- 50 receipts in ~10 minutes

## Version

2.0 - February 2026
