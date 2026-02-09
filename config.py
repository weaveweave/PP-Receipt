"""
Configuration file for Receipt Extraction Pipeline
"""

import os

# ============================================================================
# PROJECT DIRECTORIES
# ============================================================================

# Base project directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Input directory (put your PDF receipts here)
INPUT_PDF_DIR = os.path.join(BASE_DIR, "input_pdfs")

# Output directories
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
STEP1_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "step1_images")
STEP2_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "step2_json")
STEP3_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "step3_excel")

# ============================================================================
# STEP 1: PDF TO IMAGE CONVERSION & OPTIMIZATION
# ============================================================================

# DPI for PDF to image conversion (higher = better quality, but larger files)
# 300 DPI is standard for document scanning
PDF_TO_IMAGE_DPI = 250

# Image format for output
IMAGE_FORMAT = "PNG"  # PNG is lossless, good for text documents

# Image size optimization (for LM Studio API efficiency)
# Images will be resized during preprocessing if they exceed this size
MAX_IMAGE_SIZE = 1300  # Max dimension in pixels (reduces memory and bandwidth)

# Image preprocessing options
ENABLE_GRAYSCALE = True  # Convert to grayscale (reduces noise, improves OCR)
ENABLE_DESKEW = False # Auto-correct skewed/rotated images
ENABLE_CONTRAST_ENHANCEMENT = False  # Enhance contrast for better readability
ENABLE_NOISE_REDUCTION = False  # Remove noise from scanned documents
ENABLE_BINARIZATION = False  # Convert to pure black & white (optional, can be too aggressive)

# Deskew sensitivity (degrees)
DESKEW_ANGLE_THRESHOLD = 0.5  # Minimum angle to trigger deskew

# ============================================================================
# STEP 2: IMAGE TO JSON EXTRACTION VIA LM STUDIO
# ============================================================================

# LM Studio server configuration
LM_STUDIO_BASE_URL = "http://localhost:1234"

# Model selection - uncomment the model you want to use
# Make sure the model is loaded in LM Studio before running!

# Option 1: Qwen3-VL (RECOMMENDED - Best overall performance)
LM_STUDIO_MODEL = "qwen3-vl"

# Option 2: OLMoCR 2 by Allen AI
#LM_STUDIO_MODEL = "olmocr-2"

# API request settings
REQUEST_TIMEOUT = 180  # Timeout in seconds (3 minutes)
MAX_RETRIES = 3  # Number of retries for failed API calls
RETRY_BASE_DELAY = 2  # Base delay for exponential backoff (seconds)

# LLM generation parameters
TEMPERATURE = 0.1  # Low temperature for more deterministic outputs
MAX_TOKENS = 1000  # Maximum tokens in response

# ============================================================================
# STEP 3: JSON TO EXCEL CONVERSION
# ============================================================================

# Excel output filename
EXCEL_OUTPUT_FILENAME = "Rekapitulasi_Kuitansi.xlsx"

# Excel sheet name
EXCEL_SHEET_NAME = "Data Kuitansi"

# Column headers for Excel (in order)
EXCEL_COLUMNS = [
    "No. Kuitansi",
    "Tanggal",
    "Penerima",
    "Uang Sejumlah (Rp)",
    "Jumlah (Liter)",
    "Keterangan"
]

# Excel formatting options
EXCEL_AUTO_WIDTH = True  # Auto-adjust column widths
EXCEL_FREEZE_HEADER = True  # Freeze first row (header)
EXCEL_ADD_BORDERS = True  # Add borders to cells
EXCEL_HEADER_BOLD = True  # Make header text bold

# ============================================================================
# PARALLEL PROCESSING (MacBook Air M2 16GB RAM)
# ============================================================================

# Maximum concurrent workers for parallel processing
# Auto-calculated based on available RAM, but you can override
MAX_WORKERS = None  # None = auto-calculate based on RAM

# Conservative RAM allocation per worker (in GB)
# MacBook M2 16GB: We'll use ~2GB per worker = max 6-7 workers
RAM_PER_WORKER = 2.0

# Maximum workers cap (to avoid overwhelming the system)
MAX_WORKERS_CAP = 6  # Conservative for M2 16GB

# ============================================================================
# LOGGING & DEBUG
# ============================================================================

# Enable verbose logging
VERBOSE = True

# Save preprocessing debug images (before/after optimization)
SAVE_DEBUG_IMAGES = False  # Set to True to save intermediate images

# Debug output directory
DEBUG_DIR = os.path.join(OUTPUT_DIR, "debug")

# ============================================================================
# EXTRACTION PROMPT TEMPLATE
# ============================================================================

EXTRACTION_PROMPT = """Anda adalah asisten AI yang bertugas mengekstrak data dari kuitansi PT. X. dalam satu gambar ada dua kuitansi, atas dan bawah.

INSTRUKSI EKSTRASI - Ikuti dengan TELITI:

1. **no_kuitansi**: Cari angka yang muncul setelah kata "No." di bagian atas kuitansi. ambil beserta format lengkap, biasanya mengandung tanda garis miring, diakhiri tahun 2023. lalu hapus spasi apabila ada.
2. **tanggal**: Cari tanggal yang muncul setelah nama tempat misal "Jakarta, " atau "Sungai Angit, "; dan sebelum kata "Yang Menerima"(ubah menjadi format: DD-MMM-YY)
3. **penerima**: Cari nama orang yang tertulis pada receipt. biasanya di dekat signature dan kata "Yang Menerima", tapi yang dicari berupa nama orang. sesuai keyakinanmu saja, jangan berpikir terlalu lama.
4. **uang_sejumlah_rp**: Cari angka yang muncul SETELAH "Rp." di bagian tengah kuitansi (BUKAN yang ada di bagian "Uang Sejumlah"). Ambil hanya angka, tanpa titik, tanpa koma, tanpa "Rp."
5. **jumlah_liter**: Cari angka yang muncul SEBELUM kata "Liter". Ambil angka dan sertakan Liter
6. **keterangan**: Cari angka persentase yang ada dalam tanda kurung, biasanya setelah liter, kata "liter", atau "Liter". contoh: "(XX,X%)". Ambil angka dan persen

FORMAT OUTPUT:
Kembalikan hasil dalam format JSON yang valid dengan struktur berikut:

{
"receipts": [
{
"no_kuitansi": "",
"tanggal": "",
"penerima": "",
"uang_sejumlah_rp": "",
"jumlah_liter": "",
"keterangan": ""
},
{
"no_kuitansi": "",
"tanggal": "",
"penerima": "",
"uang_sejumlah_rp": "",
"jumlah_liter": "",
"keterangan": ""
}
]
}

PENTING:
- Jangan tambahkan field lain
- Jangan input multiple line dalam satu field (dilarang /n atau \n)
- Semua nilai harus berupa string
- Untuk uang_sejumlah_rp: hapus semua titik, koma, dan "Rp." - hanya angka saja
- Pastikan JSON valid (tidak ada trailing comma)
- Jika data tidak ditemukan, isi dengan string kosong ""

Ekstrak data dari gambar kuitansi berikut, dengan cepat, jangan berpikir terlalu lama dan jangan berhalusinasi:"""
# ============================================================================
# AUTO-CREATE DIRECTORIES ON IMPORT
# ============================================================================

def _create_directories():
    """Create all necessary directories if they don't exist"""
    directories = [
        INPUT_PDF_DIR,
        STEP1_OUTPUT_DIR,
        STEP2_OUTPUT_DIR,
        STEP3_OUTPUT_DIR,
    ]
    if SAVE_DEBUG_IMAGES:
        directories.append(DEBUG_DIR)
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Create directories on import
_create_directories()
