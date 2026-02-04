"""
Step 2: Extract receipt data from images using Vision LLM via LM Studio
Converts receipt images to structured JSON data
"""

import os
import json
import base64
import time
import re
from pathlib import Path
from PIL import Image
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil

from config import (
    STEP1_OUTPUT_DIR,
    STEP2_OUTPUT_DIR,
    LM_STUDIO_BASE_URL,
    LM_STUDIO_MODEL,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    RETRY_BASE_DELAY,
    MAX_IMAGE_SIZE,
    TEMPERATURE,
    MAX_TOKENS,
    EXTRACTION_PROMPT,
    MAX_WORKERS_CAP,
    RAM_PER_WORKER,
    VERBOSE
)


# ============================================================================
# LM STUDIO API CALL FUNCTION
# ============================================================================

def call_lm_studio(image_path, prompt):
    """
    Call LM Studio API with vision model to extract data from receipt image
    
    Args:
        image_path (str): Path to the receipt image file
        prompt (str): Extraction prompt
    
    Returns:
        dict: Parsed JSON response from the model
    
    Raises:
        Exception: If API call fails after all retries
    """
    
    # Resize image if necessary
    image_path = resize_image_if_needed(image_path)
    
    # Encode image to base64
    with open(image_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode("utf-8")
    
    # Determine image format
    image_ext = Path(image_path).suffix.lower()
    mime_type = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp',
        '.gif': 'image/gif'
    }.get(image_ext, 'image/jpeg')
    
    # Prepare API request payload (OpenAI-compatible format)
    payload = {
        "model": LM_STUDIO_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}"
                        }
                    }
                ]
            }
        ],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS
    }
    
    # Retry loop with exponential backoff
    for attempt in range(MAX_RETRIES):
        try:
            if VERBOSE and attempt > 0:
                print(f"    ðŸ”„ Retry attempt {attempt + 1}/{MAX_RETRIES}")
            
            # Make API call to LM Studio
            response = requests.post(
                f"{LM_STUDIO_BASE_URL}/v1/chat/completions",
                json=payload,
                timeout=REQUEST_TIMEOUT,
                headers={"Content-Type": "application/json"}
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse response
            response_json = response.json()
            
            # Extract content from OpenAI-compatible response format
            if "choices" in response_json and len(response_json["choices"]) > 0:
                content = response_json["choices"][0]["message"]["content"]
            else:
                raise ValueError("Invalid response format from LM Studio API")
            
            # Parse and clean the JSON response
            extracted_data = robust_json_parse(content)
            
            # Sanitize the extracted data
            extracted_data = sanitize_extracted_data(extracted_data)
            
            return extracted_data
            
        except requests.exceptions.Timeout:
            print(f"  â±ï¸  Timeout on attempt {attempt + 1}/{MAX_RETRIES}")
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                print(f"  â³ Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise Exception(f"API call timed out after {MAX_RETRIES} attempts")
        
        except requests.exceptions.ConnectionError:
            print(f"  âŒ Connection error - Is LM Studio running?")
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                print(f"  â³ Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise Exception(f"Cannot connect to LM Studio. Please ensure:\n"
                              f"  1. LM Studio is running\n"
                              f"  2. Server is started on {LM_STUDIO_BASE_URL}\n"
                              f"  3. Model '{LM_STUDIO_MODEL}' is loaded")
        
        except requests.exceptions.RequestException as e:
            print(f"  âŒ Request error on attempt {attempt + 1}/{MAX_RETRIES}: {e}")
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                print(f"  â³ Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise Exception(f"API request failed after {MAX_RETRIES} attempts: {e}")
        
        except (json.JSONDecodeError, ValueError) as e:
            print(f"  âš ï¸  Parse error on attempt {attempt + 1}/{MAX_RETRIES}: {e}")
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                print(f"  â³ Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise Exception(f"Failed to parse response after {MAX_RETRIES} attempts: {e}")


# ============================================================================
# ROBUST JSON PARSER
# ============================================================================

def robust_json_parse(text):
    """
    Robustly parse JSON from LLM response with multiple fallback strategies
    
    Args:
        text (str): Raw text response from LLM
    
    Returns:
        dict: Parsed JSON object
    
    Raises:
        json.JSONDecodeError: If all parsing strategies fail
    """
    
    # Strategy 1: Pre-clean common issues
    cleaned = text.strip()
    
    # Remove trailing commas before closing braces/brackets
    cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
    
    # Strategy 2: Try to parse directly
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    # Strategy 3: Extract from markdown code block
    json_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_block_match:
        try:
            extracted = json_block_match.group(1)
            # Clean trailing commas again
            extracted = re.sub(r',(\s*[}\]])', r'\1', extracted)
            return json.loads(extracted)
        except json.JSONDecodeError:
            pass
    
    # Strategy 4: Extract first {...} block
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            extracted = json_match.group(0)
            # Clean trailing commas again
            extracted = re.sub(r',(\s*[}\]])', r'\1', extracted)
            return json.loads(extracted)
        except json.JSONDecodeError:
            pass
    
    # If all strategies fail, raise error
    raise json.JSONDecodeError(
        f"Could not parse JSON from response. Text preview: {text[:200]}...",
        text,
        0
    )


# ============================================================================
# DATA SANITIZATION
# ============================================================================

def sanitize_extracted_data(data):
    """
    Sanitize extracted data: clean number formats, remove prefixes/suffixes
    
    Args:
        data (dict): Raw extracted data
    
    Returns:
        dict: Sanitized data
    """
    
    sanitized = data.copy()
    
    # Clean uang_sejumlah_rp: remove "Rp.", dots, commas
    if "uang_sejumlah_rp" in sanitized:
        value = str(sanitized["uang_sejumlah_rp"])
        # Remove "Rp." prefix
        value = re.sub(r'Rp\.?\s*', '', value, flags=re.IGNORECASE)
        # Remove dots and commas (Indonesian number format)
        value = value.replace('.', '').replace(',', '')
        # Keep only digits
        value = re.sub(r'[^\d]', '', value)
        sanitized["uang_sejumlah_rp"] = value
    
    # Clean jumlah_liter: remove "Liter" suffix, dots, commas
    if "jumlah_liter" in sanitized:
        value = str(sanitized["jumlah_liter"])
        # Remove "Liter" suffix
        value = re.sub(r'\s*Liter.*$', '', value, flags=re.IGNORECASE)
        # Remove dots and commas
        value = value.replace('.', '').replace(',', '')
        # Keep only digits
        value = re.sub(r'[^\d]', '', value)
        sanitized["jumlah_liter"] = value
    
    # Ensure all values are strings
    for key in sanitized:
        if sanitized[key] is None:
            sanitized[key] = ""
        else:
            sanitized[key] = str(sanitized[key])
    
    return sanitized


# ============================================================================
# IMAGE PROCESSING
# ============================================================================

def resize_image_if_needed(image_path):
    """
    Resize image if it exceeds MAX_IMAGE_SIZE to save memory and bandwidth
    
    Args:
        image_path (str): Path to original image
    
    Returns:
        str: Path to resized image (or original if no resize needed)
    """
    
    with Image.open(image_path) as img:
        width, height = img.size
        max_dim = max(width, height)
        
        if max_dim <= MAX_IMAGE_SIZE:
            return image_path
        
        # Calculate new dimensions
        scale = MAX_IMAGE_SIZE / max_dim
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # Resize and save
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save to temp file
        resized_path = image_path.replace('.', '_resized.')
        resized.save(resized_path, quality=90)
        
        if VERBOSE:
            print(f"    ðŸ“ Resized {width}x{height} â†’ {new_width}x{new_height}")
        return resized_path


# ============================================================================
# PARALLEL PROCESSING
# ============================================================================

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
    
    print(f"ðŸ’¾ Available RAM: {available_ram_gb:.1f} GB")
    print(f"ðŸ‘· Max workers: {max_workers}")
    
    return max_workers


def process_single_image(image_path, output_dir):
    """
    Process a single receipt image: extract data and save JSON
    
    Args:
        image_path (str): Path to receipt image
        output_dir (str): Directory to save JSON output
    
    Returns:
        tuple: (image_name, success_status, extracted_data or error_message)
    """
    
    image_name = Path(image_path).name
    print(f"\nðŸ” Processing: {image_name}")
    
    try:
        # Call LM Studio API
        if VERBOSE:
            print(f"  ðŸ¤– Calling LM Studio ({LM_STUDIO_MODEL})...")
        
        extracted_data = call_lm_studio(image_path, EXTRACTION_PROMPT)
        
        # Save to JSON file
        json_filename = Path(image_path).stem + ".json"
        json_path = os.path.join(output_dir, json_filename)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, indent=2, ensure_ascii=False)
        
        print(f"âœ… Success: {image_name} â†’ {json_filename}")
        
        # Print extracted data preview
        if VERBOSE:
            print(f"  ðŸ“‹ Preview:")
            print(f"    - No. Kuitansi: {extracted_data.get('no_kuitansi', 'N/A')}")
            print(f"    - Tanggal: {extracted_data.get('tanggal', 'N/A')}")
            print(f"    - Penerima: {extracted_data.get('penerima', 'N/A')}")
        
        return (image_name, True, extracted_data)
    
    except Exception as e:
        print(f"âŒ Failed: {image_name}")
        print(f"  Error: {str(e)}")
        return (image_name, False, str(e))


def process_images_parallel(image_dir, output_dir):
    """
    Process all images in parallel using ThreadPoolExecutor
    
    Args:
        image_dir (str): Directory containing receipt images
        output_dir (str): Directory to save JSON outputs
    
    Returns:
        dict: Summary statistics
    """
    
    # Get list of image files
    image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
    image_files = [
        os.path.join(image_dir, f)
        for f in os.listdir(image_dir)
        if Path(f).suffix.lower() in image_extensions
    ]
    
    if not image_files:
        print("âš ï¸  No image files found in input directory!")
        return {"total": 0, "success": 0, "failed": 0}
    
    print(f"\nðŸ“Š Found {len(image_files)} image(s) to process")
    print("=" * 60)
    
    # Calculate optimal number of workers
    max_workers = calculate_max_workers()
    
    # Process images in parallel
    results = {"total": len(image_files), "success": 0, "failed": 0, "errors": []}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_image = {
            executor.submit(process_single_image, img_path, output_dir): img_path
            for img_path in image_files
        }
        
        # Process completed tasks
        for future in as_completed(future_to_image):
            image_name, success, data = future.result()
            
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({"image": image_name, "error": data})
    
    # Print summary
    print("\n" + "=" * 60)
    print("ðŸ“ˆ PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Total images: {results['total']}")
    print(f"âœ… Success: {results['success']}")
    print(f"âŒ Failed: {results['failed']}")
    
    if results["errors"]:
        print("\nâš ï¸  Errors:")
        for err in results["errors"]:
            print(f"  - {err['image']}: {err['error']}")
    
    return results


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""
    
    print("=" * 60)
    print("ðŸš€ STEP 2: EXTRACT DATA FROM RECEIPT IMAGES")
    print("=" * 60)
    print(f"Input directory: {STEP1_OUTPUT_DIR}")
    print(f"Output directory: {STEP2_OUTPUT_DIR}")
    print(f"\nâš™ï¸  LM Studio settings:")
    print(f"  - Server: {LM_STUDIO_BASE_URL}")
    print(f"  - Model: {LM_STUDIO_MODEL}")
    print(f"  - Temperature: {TEMPERATURE}")
    print(f"  - Max tokens: {MAX_TOKENS}")
    
    # Check if LM Studio is accessible
    try:
        print(f"\nðŸ” Checking LM Studio connection...")
        response = requests.get(f"{LM_STUDIO_BASE_URL}/v1/models", timeout=5)
        response.raise_for_status()
        print(f"âœ… LM Studio is running and accessible")
    except Exception as e:
        print(f"âŒ Cannot connect to LM Studio!")
        print(f"   Error: {e}")
        print(f"\nðŸ“ Please ensure:")
        print(f"   1. LM Studio is running")
        print(f"   2. Server is started (Local Server tab)")
        print(f"   3. Model '{LM_STUDIO_MODEL}' is loaded")
        print(f"   4. Server URL is {LM_STUDIO_BASE_URL}")
        return
    
    # Check if input directory exists and has files
    if not os.path.exists(STEP1_OUTPUT_DIR):
        print(f"\nâŒ Error: Input directory not found: {STEP1_OUTPUT_DIR}")
        print("   Please run step1_pdf_to_images.py first")
        return
    
    # Process all images
    results = process_images_parallel(STEP1_OUTPUT_DIR, STEP2_OUTPUT_DIR)
    
    print("\nâœ¨ Step 2 completed!")
    print(f"ðŸ“ Output saved to: {STEP2_OUTPUT_DIR}")
    
    if results["success"] > 0:
        print(f"\nâž¡ï¸  Next step: Run step3_json_to_excel.py to create Excel spreadsheet")


if __name__ == "__main__":
    main()
