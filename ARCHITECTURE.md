# Architecture

## Overview

```
PDF Files → Step 1 → Images → Step 2 → JSON → Step 3 → Excel
```

## Step 1: PDF to Optimized Images

**Input:** `input_pdfs/*.pdf`  
**Output:** `output/step1_images/*.png`

**Process:**
1. Convert PDF to 300 DPI images
2. Grayscale conversion
3. Auto-deskew (rotation correction)
4. Contrast enhancement (CLAHE)
5. Noise reduction

**Parallel Processing:** 6 workers (configurable)

## Step 2: Images to JSON Data

**Input:** `output/step1_images/*.png`  
**Output:** `output/step2_json/*.json`

**Process:**
1. Resize images if needed (max 1500px)
2. Encode to base64
3. Send to LM Studio Vision API
4. Parse JSON response
5. Sanitize data (remove formatting)

**API:** OpenAI-compatible format  
**Model:** Qwen3-VL (recommended)  
**Retry Logic:** 3 attempts with exponential backoff

## Step 3: JSON to Excel

**Input:** `output/step2_json/*.json`  
**Output:** `output/step3_excel/Rekapitulasi_Kuitansi.xlsx`

**Process:**
1. Load all JSON files
2. Transform to DataFrame
3. Format currency (thousands separator)
4. Sort by receipt number
5. Apply Excel styling (borders, headers, auto-width)

## Data Flow

### Extracted Fields

```json
{
  "no_kuitansi": "123",
  "tanggal": "15-01-2024",
  "penerima": "BUDI SANTOSO",
  "uang_sejumlah_rp": "615000000",
  "jumlah_liter": "3000",
  "keterangan": "(80,2%)"
}
```

### Excel Output

| No. Kuitansi | Tanggal | Penerima | Uang Sejumlah (Rp) | Jumlah (Liter) | Keterangan |
|--------------|---------|----------|-------------------|----------------|------------|
| 123 | 15-01-2024 | BUDI SANTOSO | 615.000.000 | 3000 | (80,2%) |

## Performance

**MacBook M2 16GB:**
- Step 1: ~2-3 sec/page (CPU-bound)
- Step 2: ~5-10 sec/image (LLM inference)
- Step 3: <1 sec (even for 100+ rows)

**Memory Usage:**
- Per worker: ~2GB RAM
- Peak total: ~8GB for 6 workers

## Error Handling

**Network Layer:** Retry with exponential backoff  
**Parsing Layer:** Multiple JSON extraction strategies  
**Data Layer:** Sanitization and validation

## Configuration

All settings in `config.py`:
- Preprocessing options
- LM Studio connection
- Parallel processing limits
- Excel formatting
