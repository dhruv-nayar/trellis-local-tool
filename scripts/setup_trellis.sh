#!/bin/bash

# TRELLIS Setup Script
# This script installs TRELLIS and its dependencies

set -e

echo "========================================="
echo "TRELLIS Local Tool - Setup Script"
echo "========================================="
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "WARNING: TRELLIS officially supports Linux only."
    echo "macOS and Windows may work but are not officially tested."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for CUDA
if command -v nvidia-smi &> /dev/null; then
    echo "✓ NVIDIA GPU detected"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    echo ""
else
    echo "WARNING: No NVIDIA GPU detected. TRELLIS requires a GPU with ≥16GB VRAM."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

# Create TRELLIS directory if it doesn't exist
TRELLIS_DIR="${HOME}/.cache/trellis/repo"
mkdir -p "$(dirname "$TRELLIS_DIR")"

# Clone TRELLIS repository
if [ ! -d "$TRELLIS_DIR" ]; then
    echo "Cloning TRELLIS repository..."
    git clone --recursive https://github.com/microsoft/TRELLIS.git "$TRELLIS_DIR"
else
    echo "TRELLIS repository already exists at $TRELLIS_DIR"
    read -p "Update existing repository? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$TRELLIS_DIR"
        git pull
        git submodule update --init --recursive
    fi
fi

# Run TRELLIS setup
cd "$TRELLIS_DIR"
echo ""
echo "Running TRELLIS setup.sh..."

# Detect CUDA version
if command -v nvcc &> /dev/null; then
    CUDA_VERSION=$(nvcc --version | grep "release" | awk '{print $5}' | cut -d',' -f1)
    echo "Detected CUDA version: $CUDA_VERSION"

    if [[ $CUDA_VERSION == 11.8* ]]; then
        CUDA_FLAG="--cuda118"
    elif [[ $CUDA_VERSION == 12.* ]]; then
        CUDA_FLAG="--cuda122"
    else
        echo "WARNING: Unsupported CUDA version. Using CUDA 12.2 by default."
        CUDA_FLAG="--cuda122"
    fi
else
    echo "WARNING: nvcc not found. Using CUDA 12.2 by default."
    CUDA_FLAG="--cuda122"
fi

# Run setup with appropriate flags
if [ -f "setup.sh" ]; then
    chmod +x setup.sh
    ./setup.sh $CUDA_FLAG --xformers
else
    echo "ERROR: setup.sh not found in TRELLIS repository"
    exit 1
fi

echo ""
echo "========================================="
echo "✓ TRELLIS setup complete!"
echo "========================================="
echo ""
echo "TRELLIS installed at: $TRELLIS_DIR"
echo ""
echo "Next steps:"
echo "1. Install this tool: pip install -e ."
echo "2. Run setup command: trellis-tool setup"
echo "3. Convert images: trellis-tool convert image.jpg"
echo ""
