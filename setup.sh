#!/bin/bash

# Setup script for Receipt Pipeline on MacBook M2
# This script will check and install all necessary dependencies

echo "=========================================="
echo "  Receipt Pipeline - Setup Script"
echo "  MacBook M2 Installation"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}âœ… $1${NC}"
}

print_error() {
    echo -e "${RED}âŒ $1${NC}"
}

print_info() {
    echo -e "${BLUE}â„¹ï¸  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}âš ï¸  $1${NC}"
}

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This script is designed for macOS only"
    exit 1
fi

print_success "Running on macOS"

# Check if running on Apple Silicon
if [[ $(uname -m) != "arm64" ]]; then
    print_warning "This script is optimized for Apple Silicon (M1/M2/M3)"
    print_info "It should still work on Intel Macs, but some optimizations may not apply"
fi

# Check Python version
echo ""
print_info "Checking Python installation..."

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python $PYTHON_VERSION found"
    
    # Check if Python version is 3.9 or higher
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
        print_error "Python 3.9 or higher is required. Found: $PYTHON_VERSION"
        exit 1
    fi
else
    print_error "Python 3 not found. Please install Python 3.9 or higher"
    exit 1
fi

# Check Homebrew
echo ""
print_info "Checking Homebrew installation..."

if command -v brew &> /dev/null; then
    print_success "Homebrew found"
else
    print_warning "Homebrew not found"
    print_info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    if [ $? -eq 0 ]; then
        print_success "Homebrew installed successfully"
    else
        print_error "Failed to install Homebrew"
        exit 1
    fi
fi

# Check and install Poppler
echo ""
print_info "Checking Poppler installation (required for PDF processing)..."

if brew list poppler &> /dev/null; then
    print_success "Poppler already installed"
else
    print_warning "Poppler not found"
    print_info "Installing Poppler via Homebrew..."
    brew install poppler
    
    if [ $? -eq 0 ]; then
        print_success "Poppler installed successfully"
    else
        print_error "Failed to install Poppler"
        exit 1
    fi
fi

# Install Python dependencies
echo ""
print_info "Installing Python dependencies..."

if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        print_success "Python dependencies installed successfully"
    else
        print_error "Failed to install Python dependencies"
        exit 1
    fi
else
    print_error "requirements.txt not found in current directory"
    exit 1
fi

# Verify installations
echo ""
print_info "Verifying installations..."

python3 -c "import cv2, PIL, pdf2image, openpyxl, pandas, numpy, requests, psutil" 2>/dev/null

if [ $? -eq 0 ]; then
    print_success "All Python packages verified"
else
    print_error "Some Python packages failed to import"
    print_info "Try running: pip3 install -r requirements.txt"
    exit 1
fi

# Create directory structure
echo ""
print_info "Creating directory structure..."

mkdir -p input_pdfs
mkdir -p output/step1_images
mkdir -p output/step2_json
mkdir -p output/step3_excel

print_success "Directories created"

# Check LM Studio (optional)
echo ""
print_info "Checking LM Studio installation..."

if [ -d "/Applications/LM Studio.app" ]; then
    print_success "LM Studio found in Applications"
else
    print_warning "LM Studio not found"
    print_info "Please download and install LM Studio from: https://lmstudio.ai"
    print_info "This is REQUIRED to run Step 2 (image â†’ JSON extraction)"
fi

# Summary
echo ""
echo "=========================================="
echo "  Setup Summary"
echo "=========================================="
print_success "Python $PYTHON_VERSION"
print_success "Homebrew installed"
print_success "Poppler installed"
print_success "Python dependencies installed"
print_success "Directory structure created"

echo ""
echo "=========================================="
echo "  Next Steps"
echo "=========================================="
echo ""
echo "1. Install LM Studio (if not already installed):"
echo "   https://lmstudio.ai"
echo ""
echo "2. Download a Vision model in LM Studio:"
echo "   - Qwen3-VL (recommended)"
echo "   - Ministral 3"
echo "   - OLMoCR 2"
echo ""
echo "3. Start LM Studio server:"
echo "   - Open LM Studio"
echo "   - Go to 'Local Server' tab"
echo "   - Load your model"
echo "   - Click 'Start Server'"
echo ""
echo "4. Put your PDF receipts in: input_pdfs/"
echo ""
echo "5. Run the pipeline:"
echo "   python3 run_pipeline.py"
echo ""
echo "=========================================="

print_success "Setup completed!"
echo ""
