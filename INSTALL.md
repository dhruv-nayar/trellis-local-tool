# Installation Guide

Detailed installation instructions for the TRELLIS Local Tool.

## Prerequisites

### Hardware Requirements

- **GPU**: NVIDIA GPU with ≥16GB VRAM
  - Recommended: A100 (40GB), A6000 (48GB), or RTX 4090 (24GB)
  - Minimum: RTX 3090 (24GB), RTX 4080 (16GB)
- **RAM**: ≥32GB system RAM recommended
- **Storage**: ~10GB free space for models and cache

### Software Requirements

- **OS**: Linux (Ubuntu 20.04+, Debian 11+, or similar)
  - macOS: Experimental support (Apple Silicon not supported)
  - Windows: Use WSL2 with Ubuntu
- **Python**: 3.8, 3.9, 3.10, or 3.11
- **CUDA**: 11.8 or 12.2
- **Git**: With submodule support

## Installation Steps

### 1. System Setup

#### Ubuntu/Debian

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
    git \
    python3 python3-pip python3-venv \
    build-essential \
    cuda-toolkit-12-2  # or cuda-toolkit-11-8

# Verify CUDA
nvcc --version
nvidia-smi
```

#### macOS

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 git

# Note: CUDA not available on macOS, CPU mode only
```

#### Windows (WSL2)

```bash
# Open PowerShell as Administrator and install WSL2
wsl --install -d Ubuntu-22.04

# Open Ubuntu terminal and follow Ubuntu/Debian instructions above
```

### 2. Clone Repository

```bash
git clone https://github.com/yourusername/trellis-local-tool.git
cd trellis-local-tool
```

### 3. Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate  # Windows PowerShell
```

### 4. Install TRELLIS

The setup script handles TRELLIS installation automatically:

```bash
chmod +x scripts/setup_trellis.sh
./scripts/setup_trellis.sh
```

The script will:
1. Check system requirements
2. Clone TRELLIS repository to `~/.cache/trellis/repo`
3. Install PyTorch with CUDA support
4. Install xFormers for efficient attention
5. Install TRELLIS dependencies

**Manual Installation** (if script fails):

```bash
# Clone TRELLIS
mkdir -p ~/.cache/trellis
cd ~/.cache/trellis
git clone --recursive https://github.com/microsoft/TRELLIS.git repo
cd repo

# Install dependencies (CUDA 12.2)
./setup.sh --cuda122 --xformers

# Or for CUDA 11.8
./setup.sh --cuda118 --xformers
```

### 5. Install TRELLIS Local Tool

```bash
cd /path/to/trellis-local-tool

# Install in development mode
pip install -e .

# Or install normally
pip install .
```

### 6. Verify Installation

```bash
# Check if command is available
trellis-tool --version

# Download model (this may take a few minutes)
trellis-tool setup

# Test with a sample image
trellis-tool info examples/sample.jpg  # If you have a test image
```

## Alternative Installation Methods

### Using Conda

```bash
# Create conda environment
conda create -n trellis python=3.10
conda activate trellis

# Install CUDA toolkit
conda install -c nvidia cuda-toolkit=12.2

# Install PyTorch
conda install pytorch torchvision pytorch-cuda=12.1 -c pytorch -c nvidia

# Install tool
pip install -e .
```

### Using Docker (Coming Soon)

```bash
# Build Docker image
docker build -t trellis-tool .

# Run container
docker run --gpus all -v $(pwd):/workspace trellis-tool convert image.jpg
```

## Troubleshooting

### CUDA Not Found

```bash
# Check CUDA installation
nvcc --version
nvidia-smi

# Add CUDA to PATH (add to ~/.bashrc)
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
```

### PyTorch CUDA Mismatch

```bash
# Check PyTorch CUDA version
python -c "import torch; print(torch.version.cuda)"

# Reinstall PyTorch with correct CUDA version
pip uninstall torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### Import Errors

```bash
# Ensure TRELLIS is in Python path
export PYTHONPATH="$HOME/.cache/trellis/repo:$PYTHONPATH"

# Or add to ~/.bashrc for permanent fix
echo 'export PYTHONPATH="$HOME/.cache/trellis/repo:$PYTHONPATH"' >> ~/.bashrc
source ~/.bashrc
```

### Out of Memory

```bash
# Monitor GPU memory
watch -n 1 nvidia-smi

# Reduce batch size or use CPU
trellis-tool convert image.jpg --device cpu

# Increase CUDA memory allocation
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

### Permission Denied

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Fix ownership
sudo chown -R $USER:$USER ~/.cache/trellis
```

## Updating

### Update TRELLIS Local Tool

```bash
cd trellis-local-tool
git pull
pip install -e . --upgrade
```

### Update TRELLIS

```bash
cd ~/.cache/trellis/repo
git pull
git submodule update --init --recursive
./setup.sh --cuda122 --xformers
```

### Update Models

```bash
# Clear model cache
rm -rf ~/.cache/trellis/models

# Re-download models
trellis-tool setup
```

## Uninstallation

```bash
# Uninstall package
pip uninstall trellis-local-tool

# Remove TRELLIS
rm -rf ~/.cache/trellis

# Remove virtual environment
rm -rf venv
```

## Next Steps

After installation:

1. Read the [README.md](README.md) for usage instructions
2. Try the [examples](examples/README.md)
3. Configure settings in `config.yaml`
4. Start converting images!

## Support

If you encounter issues:

1. Check the [troubleshooting section](#troubleshooting)
2. Review [TRELLIS installation docs](https://github.com/microsoft/TRELLIS#installation)
3. Open an [issue on GitHub](https://github.com/yourusername/trellis-local-tool/issues)
