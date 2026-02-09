"""
Step 1: Convert PDF receipts to optimized images
Features:
- PDF to image conversion (300 DPI)
- Grayscale conversion
- Auto-deskew (correct rotation)
- Contrast enhancement
- Noise reduction
- Optional binarization
- Auto-resize for LM Studio API optimization
"""

import os
import sys
from pathlib import Path
import numpy as np
import cv2
from PIL import Image
from pdf2image import convert_from_path
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil

from config import (
    INPUT_PDF_DIR,
    STEP1_OUTPUT_DIR,
    PDF_TO_IMAGE_DPI,
    IMAGE_FORMAT,
    MAX_IMAGE_SIZE,
    ENABLE_GRAYSCALE,
    ENABLE_DESKEW,
    ENABLE_CONTRAST_ENHANCEMENT,
    ENABLE_NOISE_REDUCTION,
    ENABLE_BINARIZATION,
    DESKEW_ANGLE_THRESHOLD,
    SAVE_DEBUG_IMAGES,
    DEBUG_DIR,
    MAX_WORKERS_CAP,
    RAM_PER_WORKER,
    VERBOSE
)


# ============================================================================
# IMAGE PREPROCESSING FUNCTIONS
# ============================================================================

def convert_to_grayscale(image):
    """Convert image to grayscale"""
    if len(image.shape) == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image


def deskew_image(image, debug_name=None):
    """
    Automatically detect and correct image skew/rotation
    Uses Hough Line Transform to detect document edges
    """
    gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # Detect lines using Hough Transform
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
    
    if lines is None:
        if VERBOSE:
            print(f"    ⚠️  No lines detected for deskew")
        return image
    
    # Calculate angles
    angles = []
    for line in lines:
        rho, theta = line[0]
        angle = np.degrees(theta) - 90
        angles.append(angle)
    
    # Find median angle
    median_angle = np.median(angles)
    
    # Only rotate if angle is significant
    if abs(median_angle) < DESKEW_ANGLE_THRESHOLD:
        if VERBOSE:
            print(f"    ✓ Skew angle {median_angle:.2f}° is negligible, skipping deskew")
        return image
    
    if VERBOSE:
        print(f"    🔄 Deskewing by {median_angle:.2f}°")
    
    # Rotate image
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(
        image, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )
    
    if SAVE_DEBUG_IMAGES and debug_name:
        debug_path = os.path.join(DEBUG_DIR, f"{debug_name}_deskewed.png")
        cv2.imwrite(debug_path, rotated)
    
    return rotated


def enhance_contrast(image):
    """
    Enhance image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
    Better than simple histogram equalization for document images
    """
    gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    if VERBOSE:
        print(f"    ✓ Contrast enhanced")
    
    return enhanced


def reduce_noise(image):
    """
    Reduce noise using Non-Local Means Denoising
    Preserves edges while removing noise
    """
    gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply denoising
    denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
    
    if VERBOSE:
        print(f"    ✓ Noise reduced")
    
    return denoised


def binarize_image(image):
    """
    Convert to pure black and white using adaptive thresholding
    Good for very clear text extraction, but can be too aggressive
    """
    gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Adaptive thresholding (better than simple thresholding)
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2
    )
    
    if VERBOSE:
        print(f"    ✓ Binarized (black & white)")
    
    return binary


def resize_if_needed(image):
    """
    Resize image if it exceeds MAX_IMAGE_SIZE to optimize for LM Studio API
    This reduces memory usage and bandwidth without significant quality loss
    
    Args:
        image: numpy array of image
    
    Returns:
        Resized image as numpy array (or original if no resize needed)
    """
    height, width = image.shape[:2]
    max_dim = max(height, width)
    
    if max_dim <= MAX_IMAGE_SIZE:
        return image
    
    # Calculate new dimensions
    scale = MAX_IMAGE_SIZE / max_dim
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    # Resize using high-quality interpolation
    resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
    
    if VERBOSE:
        print(f"    📏 Resized {width}x{height} → {new_width}x{new_height}")
    
    return resized


def preprocess_image(image_array, debug_name=None):
    """
    Apply all enabled preprocessing steps to image
    
    Args:
        image_array: numpy array of image
        debug_name: optional name for debug output
    
    Returns:
        Preprocessed image as numpy array
    """
    img = image_array.copy()
    
    # Step 1: Convert to grayscale
    if ENABLE_GRAYSCALE:
        if VERBOSE:
            print(f"    → Grayscale conversion")
        img = convert_to_grayscale(img)
    
    # Step 2: Deskew (correct rotation)
    if ENABLE_DESKEW:
        if VERBOSE:
            print(f"    → Auto-deskew")
        img = deskew_image(img, debug_name)
    
    # Step 3: Enhance contrast
    if ENABLE_CONTRAST_ENHANCEMENT:
        if VERBOSE:
            print(f"    → Contrast enhancement")
        img = enhance_contrast(img)
    
    # Step 4: Reduce noise
    if ENABLE_NOISE_REDUCTION:
        if VERBOSE:
            print(f"    → Noise reduction")
        img = reduce_noise(img)
    
    # Step 5: Binarization (optional, can be aggressive)
    if ENABLE_BINARIZATION:
        if VERBOSE:
            print(f"    → Binarization")
        img = binarize_image(img)
    
    # Step 6: Resize if needed (optimize for LM Studio API)
    if VERBOSE:
        print(f"    → Size optimization")
    img = resize_if_needed(img)
    
    return img


# ============================================================================
# PDF PROCESSING
# ============================================================================

def process_single_pdf(pdf_path, output_dir):
    """
    Process a single PDF file: convert to images and apply preprocessing
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save output images
    
    Returns:
        tuple: (pdf_name, success, num_pages or error_message)
    """
    pdf_name = Path(pdf_path).name
    print(f"\n📄 Processing: {pdf_name}")
    
    try:
        # Convert PDF to images
        if VERBOSE:
            print(f"  🔄 Converting PDF to images (DPI: {PDF_TO_IMAGE_DPI})...")
        
        images = convert_from_path(
            pdf_path,
            dpi=PDF_TO_IMAGE_DPI,
            fmt=IMAGE_FORMAT.lower()
        )
        
        num_pages = len(images)
        print(f"  📊 Found {num_pages} page(s)")
        
        # Process each page
        for page_num, pil_image in enumerate(images, start=1):
            print(f"  🔒 Processing page {page_num}/{num_pages}")
            
            # Convert PIL Image to numpy array
            img_array = np.array(pil_image)
            
            # Convert RGB to BGR (OpenCV format)
            if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # Save original if debug mode
            if SAVE_DEBUG_IMAGES:
                debug_name = f"{Path(pdf_name).stem}_page{page_num}"
                original_path = os.path.join(DEBUG_DIR, f"{debug_name}_original.png")
                cv2.imwrite(original_path, img_array)
            
            # Apply preprocessing (includes resize)
            print(f"  🔧 Applying preprocessing...")
            processed = preprocess_image(
                img_array,
                debug_name=f"{Path(pdf_name).stem}_page{page_num}" if SAVE_DEBUG_IMAGES else None
            )
            
            # Generate output filename
            if num_pages == 1:
                output_filename = f"{Path(pdf_name).stem}.{IMAGE_FORMAT.lower()}"
            else:
                output_filename = f"{Path(pdf_name).stem}_page{page_num}.{IMAGE_FORMAT.lower()}"
            
            output_path = os.path.join(output_dir, output_filename)
            
            # Save processed image
            cv2.imwrite(output_path, processed)
            print(f"  ✅ Saved: {output_filename}")
        
        print(f"✅ Success: {pdf_name} ({num_pages} page(s))")
        return (pdf_name, True, num_pages)
    
    except Exception as e:
        print(f"❌ Failed: {pdf_name} - {str(e)}")
        return (pdf_name, False, str(e))


def calculate_max_workers():
    """
    Calculate optimal number of workers based on available RAM
    Conservative for MacBook M2 16GB
    """
    available_ram_gb = psutil.virtual_memory().available / (1024 ** 3)
    
    # Calculate based on RAM per worker
    max_workers = max(1, int(available_ram_gb / RAM_PER_WORKER))
    
    # Cap at maximum
    max_workers = min(max_workers, MAX_WORKERS_CAP)
    
    print(f"💾 Available RAM: {available_ram_gb:.1f} GB")
    print(f"👷 Max workers: {max_workers}")
    
    return max_workers


def process_all_pdfs(input_dir, output_dir):
    """
    Process all PDF files in input directory with parallel processing
    
    Args:
        input_dir: Directory containing PDF files
        output_dir: Directory to save output images
    
    Returns:
        dict: Summary statistics
    """
    # Get list of PDF files
    pdf_files = [
        os.path.join(input_dir, f)
        for f in os.listdir(input_dir)
        if f.lower().endswith('.pdf')
    ]
    
    if not pdf_files:
        print("⚠️  No PDF files found in input directory!")
        return {"total": 0, "success": 0, "failed": 0}
    
    print(f"\n📊 Found {len(pdf_files)} PDF file(s) to process")
    print("=" * 60)
    
    # Calculate optimal workers
    max_workers = calculate_max_workers()
    
    # Process PDFs in parallel
    results = {"total": len(pdf_files), "success": 0, "failed": 0, "errors": [], "total_pages": 0}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_pdf = {
            executor.submit(process_single_pdf, pdf_path, output_dir): pdf_path
            for pdf_path in pdf_files
        }
        
        # Process completed tasks
        for future in as_completed(future_to_pdf):
            pdf_name, success, data = future.result()
            
            if success:
                results["success"] += 1
                results["total_pages"] += data
            else:
                results["failed"] += 1
                results["errors"].append({"pdf": pdf_name, "error": data})
    
    # Print summary
    print("\n" + "=" * 60)
    print("📈 PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Total PDFs: {results['total']}")
    print(f"✅ Success: {results['success']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"📄 Total pages processed: {results['total_pages']}")
    
    if results["errors"]:
        print("\n⚠️  Errors:")
        for err in results["errors"]:
            print(f"  - {err['pdf']}: {err['error']}")
    
    return results


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""
    
    print("=" * 60)
    print("🚀 STEP 1: PDF TO OPTIMIZED IMAGES")
    print("=" * 60)
    print(f"Input directory: {INPUT_PDF_DIR}")
    print(f"Output directory: {STEP1_OUTPUT_DIR}")
    print(f"\n⚙️  Preprocessing settings:")
    print(f"  - DPI: {PDF_TO_IMAGE_DPI}")
    print(f"  - Max image size: {MAX_IMAGE_SIZE}px")
    print(f"  - Grayscale: {ENABLE_GRAYSCALE}")
    print(f"  - Deskew: {ENABLE_DESKEW}")
    print(f"  - Contrast enhancement: {ENABLE_CONTRAST_ENHANCEMENT}")
    print(f"  - Noise reduction: {ENABLE_NOISE_REDUCTION}")
    print(f"  - Binarization: {ENABLE_BINARIZATION}")
    
    # Check if input directory exists
    if not os.path.exists(INPUT_PDF_DIR):
        print(f"\n❌ Error: Input directory not found: {INPUT_PDF_DIR}")
        print("Please create the directory and add PDF files.")
        sys.exit(1)
    
    # Process all PDFs
    results = process_all_pdfs(INPUT_PDF_DIR, STEP1_OUTPUT_DIR)
    
    print("\n✨ Step 1 completed!")
    print(f"📁 Output saved to: {STEP1_OUTPUT_DIR}")
    print(f"ℹ️  Images are pre-optimized for LM Studio API (max {MAX_IMAGE_SIZE}px)")
    
    if results["success"] > 0:
        print(f"\n➡️  Next step: Run step2_extract_data.py to extract data from images")


if __name__ == "__main__":
    main()
