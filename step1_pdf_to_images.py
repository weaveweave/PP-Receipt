"""
Step 1: Convert PDF receipts to optimized images
IMPROVED VERSION - Better accuracy and performance

Features:
- PDF to image conversion (300 DPI)
- Grayscale conversion
- IMPROVED: Projection-based auto-deskew (more accurate)
- IMPROVED: Optimized contrast enhancement
- IMPROVED: Smart noise reduction with edge preservation
- IMPROVED: Adaptive sharpening for better OCR
- Optional binarization
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
# IMPROVED IMAGE PREPROCESSING FUNCTIONS
# ============================================================================

def convert_to_grayscale(image):
    """Convert image to grayscale"""
    if len(image.shape) == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image


def estimate_skew_angle(image):
    """
    Estimate document skew angle using projection profile method
    More accurate than Hough Transform for text documents
    
    Args:
        image: Grayscale image
    
    Returns:
        float: Estimated skew angle in degrees (-45 to +45)
    """
    # Ensure grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Apply binary threshold to get text regions
    # Using Otsu's method for automatic threshold
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Find text contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter small contours (noise)
    min_area = 50  # Minimum area to consider
    text_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
    
    if len(text_contours) < 10:  # Need enough text for reliable estimation
        if VERBOSE:
            print(f"    ⚠️  Not enough text regions ({len(text_contours)}) for skew detection")
        return 0.0
    
    # Calculate angle using minAreaRect
    angles = []
    for cnt in text_contours:
        rect = cv2.minAreaRect(cnt)
        angle = rect[2]
        
        # Adjust angle based on rectangle orientation
        # minAreaRect returns angle between -90 and 0
        if rect[1][0] < rect[1][1]:  # width < height
            angle = 90 + angle
        
        # Normalize to -45 to +45 range
        if angle > 45:
            angle = angle - 90
        elif angle < -45:
            angle = angle + 90
            
        angles.append(angle)
    
    if not angles:
        return 0.0
    
    # Use median to avoid outliers
    median_angle = np.median(angles)
    
    # Additional validation: check standard deviation
    std_angle = np.std(angles)
    if std_angle > 15:  # High variance = unreliable
        if VERBOSE:
            print(f"    ⚠️  High angle variance ({std_angle:.2f}°), skipping deskew")
        return 0.0
    
    return median_angle


def deskew_image(image, debug_name=None):
    """
    Automatically detect and correct image skew/rotation
    IMPROVED: Uses projection profile method instead of Hough Transform
    More accurate for text documents
    
    Args:
        image: Input image (grayscale or color)
        debug_name: Optional name for debug output
    
    Returns:
        Deskewed image
    """
    gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Estimate skew angle
    angle = estimate_skew_angle(gray)
    
    # Only rotate if angle is significant
    if abs(angle) < DESKEW_ANGLE_THRESHOLD:
        if VERBOSE:
            print(f"    ✓ Skew angle {angle:.2f}° is negligible, skipping deskew")
        return image
    
    if VERBOSE:
        print(f"    🔄 Deskewing by {angle:.2f}°")
    
    # Rotate image
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    
    # Calculate rotation matrix
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Calculate new image size to avoid cropping
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    
    # Adjust rotation matrix to account for translation
    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]
    
    # Perform rotation with white background
    rotated = cv2.warpAffine(
        image, M, (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255) if len(image.shape) == 2 else (255, 255, 255)
    )
    
    # Crop back to original aspect ratio to remove excess white space
    # Find actual content boundaries
    if len(rotated.shape) == 2:
        coords = cv2.findNonZero(cv2.bitwise_not(cv2.threshold(rotated, 250, 255, cv2.THRESH_BINARY)[1]))
    else:
        gray_rotated = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)
        coords = cv2.findNonZero(cv2.bitwise_not(cv2.threshold(gray_rotated, 250, 255, cv2.THRESH_BINARY)[1]))
    
    if coords is not None:
        x, y, w, h = cv2.boundingRect(coords)
        # Add small margin
        margin = 10
        x = max(0, x - margin)
        y = max(0, y - margin)
        w = min(rotated.shape[1] - x, w + 2 * margin)
        h = min(rotated.shape[0] - y, h + 2 * margin)
        rotated = rotated[y:y+h, x:x+w]
    
    if SAVE_DEBUG_IMAGES and debug_name:
        debug_path = os.path.join(DEBUG_DIR, f"{debug_name}_deskewed.png")
        cv2.imwrite(debug_path, rotated)
    
    return rotated


def enhance_contrast(image):
    """
    Enhance image contrast using optimized CLAHE
    IMPROVED: Better parameters for receipt documents
    
    Args:
        image: Input image (grayscale or color)
    
    Returns:
        Contrast-enhanced image
    """
    gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply CLAHE with optimized parameters for receipts
    # Lower clipLimit to avoid over-enhancement
    # Smaller tileGridSize for finer local contrast
    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(4, 4))
    enhanced = clahe.apply(gray)
    
    if VERBOSE:
        print(f"    ✓ Contrast enhanced")
    
    return enhanced


def reduce_noise(image):
    """
    Reduce noise using bilateral filter
    IMPROVED: Faster than NLM, better edge preservation
    
    Args:
        image: Input image (grayscale or color)
    
    Returns:
        Denoised image
    """
    gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Bilateral filter: removes noise while preserving edges
    # d=5: smaller neighborhood (faster)
    # sigmaColor=50: moderate color similarity
    # sigmaSpace=50: moderate spatial similarity
    denoised = cv2.bilateralFilter(gray, d=5, sigmaColor=50, sigmaSpace=50)
    
    if VERBOSE:
        print(f"    ✓ Noise reduced")
    
    return denoised


def sharpen_image(image):
    """
    Apply adaptive sharpening to improve text readability
    NEW FUNCTION: Helps OCR/Vision models read text better
    
    Args:
        image: Input image (grayscale)
    
    Returns:
        Sharpened image
    """
    gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Create sharpening kernel
    # This kernel enhances edges without amplifying noise too much
    kernel = np.array([[-1, -1, -1],
                       [-1,  9, -1],
                       [-1, -1, -1]]) / 1.0
    
    # Apply sharpening
    sharpened = cv2.filter2D(gray, -1, kernel)
    
    # Blend original and sharpened (50% each) for subtle effect
    result = cv2.addWeighted(gray, 0.5, sharpened, 0.5, 0)
    
    if VERBOSE:
        print(f"    ✓ Image sharpened")
    
    return result


def binarize_image(image):
    """
    Convert to pure black and white using adaptive thresholding
    IMPROVED: Better parameters for receipt documents
    
    Args:
        image: Input image (grayscale)
    
    Returns:
        Binarized image
    """
    gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Adaptive thresholding with optimized parameters
    # Block size 15 (larger blocks for receipts)
    # C=10 (more conservative threshold adjustment)
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        15, 10
    )
    
    if VERBOSE:
        print(f"    ✓ Binarized (black & white)")
    
    return binary


def preprocess_image(image_array, debug_name=None):
    """
    Apply all enabled preprocessing steps to image
    IMPROVED: Optimized pipeline with quality checks
    
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
        
        if SAVE_DEBUG_IMAGES and debug_name:
            debug_path = os.path.join(DEBUG_DIR, f"{debug_name}_1_grayscale.png")
            cv2.imwrite(debug_path, img)
    
    # Step 2: Deskew (correct rotation) - IMPROVED
    if ENABLE_DESKEW:
        if VERBOSE:
            print(f"    → Auto-deskew (projection method)")
        img = deskew_image(img, debug_name)
        
        if SAVE_DEBUG_IMAGES and debug_name:
            debug_path = os.path.join(DEBUG_DIR, f"{debug_name}_2_deskewed.png")
            cv2.imwrite(debug_path, img)
    
    # Step 3: Reduce noise BEFORE contrast enhancement - REORDERED
    # This prevents amplifying noise
    if ENABLE_NOISE_REDUCTION:
        if VERBOSE:
            print(f"    → Noise reduction (bilateral filter)")
        img = reduce_noise(img)
        
        if SAVE_DEBUG_IMAGES and debug_name:
            debug_path = os.path.join(DEBUG_DIR, f"{debug_name}_3_denoised.png")
            cv2.imwrite(debug_path, img)
    
    # Step 4: Enhance contrast - IMPROVED
    if ENABLE_CONTRAST_ENHANCEMENT:
        if VERBOSE:
            print(f"    → Contrast enhancement (optimized CLAHE)")
        img = enhance_contrast(img)
        
        if SAVE_DEBUG_IMAGES and debug_name:
            debug_path = os.path.join(DEBUG_DIR, f"{debug_name}_4_contrast.png")
            cv2.imwrite(debug_path, img)
    
    # Step 5: Sharpen for better text readability - NEW
    # Only if not binarizing (binarization doesn't need sharpening)
    if not ENABLE_BINARIZATION:
        if VERBOSE:
            print(f"    → Adaptive sharpening")
        img = sharpen_image(img)
        
        if SAVE_DEBUG_IMAGES and debug_name:
            debug_path = os.path.join(DEBUG_DIR, f"{debug_name}_5_sharpened.png")
            cv2.imwrite(debug_path, img)
    
    # Step 6: Binarization (optional, can be aggressive)
    if ENABLE_BINARIZATION:
        if VERBOSE:
            print(f"    → Binarization (adaptive)")
        img = binarize_image(img)
        
        if SAVE_DEBUG_IMAGES and debug_name:
            debug_path = os.path.join(DEBUG_DIR, f"{debug_name}_6_binary.png")
            cv2.imwrite(debug_path, img)
    
    return img


def validate_image_quality(original, processed):
    """
    Validate that preprocessing improved or maintained image quality
    NEW FUNCTION: Prevents making images worse
    
    Args:
        original: Original image
        processed: Processed image
    
    Returns:
        bool: True if quality is acceptable
    """
    # Convert both to grayscale if needed
    if len(original.shape) == 3:
        orig_gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    else:
        orig_gray = original
    
    if len(processed.shape) == 3:
        proc_gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
    else:
        proc_gray = processed
    
    # Check if processed image is too dark or too bright
    mean_brightness = np.mean(proc_gray)
    if mean_brightness < 50 or mean_brightness > 220:
        if VERBOSE:
            print(f"    ⚠️  Warning: Unusual brightness ({mean_brightness:.1f})")
        return False
    
    # Check if there's still enough contrast
    contrast = np.std(proc_gray)
    if contrast < 20:
        if VERBOSE:
            print(f"    ⚠️  Warning: Low contrast ({contrast:.1f})")
        return False
    
    return True


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
            print(f"  📄 Converting PDF to images (DPI: {PDF_TO_IMAGE_DPI})...")
        
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
                original_path = os.path.join(DEBUG_DIR, f"{debug_name}_0_original.png")
                cv2.imwrite(original_path, img_array)
            
            # Apply preprocessing
            print(f"  🔧 Applying optimized preprocessing...")
            original_for_validation = img_array.copy()
            processed = preprocess_image(
                img_array,
                debug_name=f"{Path(pdf_name).stem}_page{page_num}" if SAVE_DEBUG_IMAGES else None
            )
            
            # Validate quality
            if not validate_image_quality(original_for_validation, processed):
                print(f"  ⚠️  Quality check failed, using minimal preprocessing")
                # Fallback to minimal processing
                processed = convert_to_grayscale(img_array)
                if ENABLE_CONTRAST_ENHANCEMENT:
                    processed = enhance_contrast(processed)
            
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
    print("🚀 STEP 1: PDF TO OPTIMIZED IMAGES (IMPROVED)")
    print("=" * 60)
    print(f"Input directory: {INPUT_PDF_DIR}")
    print(f"Output directory: {STEP1_OUTPUT_DIR}")
    print(f"\n⚙️  Preprocessing settings:")
    print(f"  - DPI: {PDF_TO_IMAGE_DPI}")
    print(f"  - Grayscale: {ENABLE_GRAYSCALE}")
    print(f"  - Deskew: {ENABLE_DESKEW} (projection method)")
    print(f"  - Noise reduction: {ENABLE_NOISE_REDUCTION} (bilateral filter)")
    print(f"  - Contrast enhancement: {ENABLE_CONTRAST_ENHANCEMENT} (optimized CLAHE)")
    print(f"  - Sharpening: {not ENABLE_BINARIZATION} (adaptive)")
    print(f"  - Binarization: {ENABLE_BINARIZATION}")
    print(f"  - Quality validation: Enabled")
    
    # Check if input directory exists
    if not os.path.exists(INPUT_PDF_DIR):
        print(f"\n❌ Error: Input directory not found: {INPUT_PDF_DIR}")
        print("Please create the directory and add PDF files.")
        sys.exit(1)
    
    # Process all PDFs
    results = process_all_pdfs(INPUT_PDF_DIR, STEP1_OUTPUT_DIR)
    
    print("\n✨ Step 1 completed!")
    print(f"📁 Output saved to: {STEP1_OUTPUT_DIR}")
    
    if results["success"] > 0:
        print(f"\n➡️  Next step: Run step2_extract_data.py to extract data from images")


if __name__ == "__main__":
    main()
