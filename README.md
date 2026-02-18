# TRELLIS Local Tool

A powerful CLI tool to convert images into high-quality 3D GLB files using Microsoft's TRELLIS model.

## Features

- **Simple CLI** - Easy-to-use command-line interface
- **Batch Processing** - Convert multiple images at once
- **High Quality** - Leverages TRELLIS-image-large (1.2B parameters)
- **Multiple Formats** - Export to GLB, OBJ, or PLY
- **Configurable** - YAML-based configuration system
- **GPU Accelerated** - CUDA support for fast processing
- **Progress Tracking** - Rich terminal output with progress bars

## Requirements

### Hardware
- NVIDIA GPU with ≥16GB VRAM (tested on A100/A6000)
- ~10GB disk space for models and cache

### Software
- Linux (recommended), macOS (experimental), or Windows with WSL2
- Python 3.8 or higher
- CUDA 11.8 or 12.2
- Git with submodule support

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/trellis-local-tool.git
cd trellis-local-tool
```

### 2. Install TRELLIS Dependencies

The setup script will clone TRELLIS and install all required dependencies:

```bash
./scripts/setup_trellis.sh
```

This script will:
- Check your system requirements
- Clone the TRELLIS repository
- Install PyTorch with CUDA support
- Set up xFormers for efficient attention
- Install TRELLIS-specific dependencies

### 3. Install the Tool

```bash
pip install -e .
```

### 4. Download the Model

```bash
trellis-tool setup
```

This downloads the TRELLIS-image-large model (~5GB). You only need to do this once.

## Quick Start

### Convert a Single Image

```bash
trellis-tool convert image.jpg
```

Output will be saved to `./output/image.glb`

### Specify Output Path

```bash
trellis-tool convert image.jpg --output model.glb
```

### Batch Process Multiple Images

```bash
trellis-tool batch ./images/ --output-dir ./3d-models/
```

### Recursive Search

```bash
trellis-tool batch ./photos/ --recursive --output-dir ./outputs/
```

## Usage

### Commands

#### `convert` - Convert a single image

```bash
trellis-tool convert IMAGE [OPTIONS]
```

**Options:**
- `-o, --output PATH` - Output GLB file path
- `-m, --model NAME` - Model to use (default: microsoft/TRELLIS-image-large)
- `-d, --device [auto|cuda|cpu]` - Device to use
- `-s, --seed INT` - Random seed for reproducibility
- `--texture-size [512|1024|2048|4096]` - Texture resolution
- `--optimize / --no-optimize` - Enable/disable mesh optimization
- `--target-faces INT` - Target face count for optimization

**Examples:**

```bash
# Basic conversion
trellis-tool convert photo.jpg

# High-quality output
trellis-tool convert photo.jpg --texture-size 4096 --no-optimize

# Reproducible output
trellis-tool convert photo.jpg --seed 42 --output model.glb

# Optimize for web
trellis-tool convert photo.jpg --optimize --target-faces 50000
```

#### `batch` - Process multiple images

```bash
trellis-tool batch INPUT_PATH [OPTIONS]
```

**Options:**
- `-o, --output-dir PATH` - Output directory
- `-r, --recursive` - Search subdirectories
- `-p, --pattern TEXT` - Output naming pattern
- `-m, --model NAME` - Model to use
- `-d, --device [auto|cuda|cpu]` - Device to use
- `-s, --seed INT` - Random seed

**Naming Patterns:**
- `{name}` - Original filename (default)
- `{timestamp}` - Current timestamp
- `{index}` - Image index in batch
- `{seed}` - Random seed used

**Examples:**

```bash
# Process all images in directory
trellis-tool batch ./images/

# Recursive with timestamp
trellis-tool batch ./photos/ -r -p "{name}_{timestamp}"

# Custom output directory
trellis-tool batch ./input/ -o ./output/models/
```

#### `info` - Display image information

```bash
trellis-tool info IMAGE
```

**Example:**

```bash
trellis-tool info photo.jpg
# Output:
# Image Information:
#   Path: photo.jpg
#   Format: JPEG
#   Mode: RGB
#   Size: 2048 x 1536 pixels
#   File Size: 1.85 MB
```

#### `setup` - Download and setup model

```bash
trellis-tool setup [OPTIONS]
```

**Options:**
- `-m, --model NAME` - Model to download

**Example:**

```bash
# Download default model
trellis-tool setup

# Download specific model
trellis-tool setup --model microsoft/TRELLIS-text-large
```

#### `config-show` - Display configuration

```bash
trellis-tool config-show
```

### Configuration

Create a `config.yaml` file in your project directory:

```yaml
model:
  name: "microsoft/TRELLIS-image-large"
  device: "auto"  # auto, cuda, or cpu
  cache_dir: "~/.cache/trellis"

processing:
  seed: 1
  steps: 50
  sparsity: 0.5

output:
  format: "glb"
  texture_size: 2048  # 512, 1024, 2048, 4096
  optimize: true
  target_faces: null  # null = auto
  output_dir: "./output"
  naming_pattern: "{name}"

logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  log_file: null  # null = console only
  show_progress: true
```

Load custom config:

```bash
trellis-tool --config my-config.yaml convert image.jpg
```

## Advanced Usage

### Environment Variables

```bash
# Set CUDA device
export CUDA_VISIBLE_DEVICES=0

# Increase memory limits
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

### Scripting

```bash
#!/bin/bash
# batch-convert.sh

for img in ./input/*.jpg; do
    echo "Processing: $img"
    trellis-tool convert "$img" \
        --output "./output/$(basename "$img" .jpg).glb" \
        --texture-size 2048 \
        --optimize
done
```

### Python API

```python
from trellis_tool.core.pipeline import TRELLISPipeline
from pathlib import Path

# Create pipeline
pipeline = TRELLISPipeline(
    model_name="microsoft/TRELLIS-image-large",
    device="cuda",
    seed=42,
    texture_size=2048,
    optimize=True
)

# Process image
result = pipeline.process_image(
    image_path=Path("input.jpg"),
    output_path=Path("output.glb")
)

print(f"Generated: {result}")
```

## Troubleshooting

### CUDA Out of Memory

```bash
# Reduce texture size
trellis-tool convert image.jpg --texture-size 1024

# Or use CPU (slower)
trellis-tool convert image.jpg --device cpu
```

### Model Not Found

```bash
# Re-run setup
trellis-tool setup

# Or manually specify cache directory
trellis-tool convert image.jpg --config config.yaml
```

### Import Errors

```bash
# Ensure TRELLIS is properly installed
./scripts/setup_trellis.sh

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"
```

## Performance

Typical processing times on NVIDIA A100 (40GB):

| Image Size | Texture Size | Time | Output Size |
|------------|--------------|------|-------------|
| 1024x1024  | 2048         | ~30s | ~15 MB      |
| 2048x2048  | 2048         | ~45s | ~25 MB      |
| 1024x1024  | 4096         | ~60s | ~40 MB      |

*Times include model inference and GLB export*

## Supported Image Formats

- JPEG/JPG
- PNG
- WebP
- BMP
- TIFF

## Output Formats

- **GLB** (default) - Binary glTF, widely supported
- **OBJ** - Wavefront, legacy format
- **PLY** - Polygon File Format, for research

## Project Structure

```
trellis-local-tool/
├── src/trellis_tool/
│   ├── cli.py              # CLI interface
│   ├── core/
│   │   ├── pipeline.py     # Main conversion pipeline
│   │   ├── model.py        # Model manager
│   │   └── exporter.py     # GLB export
│   └── utils/
│       ├── config.py       # Configuration management
│       ├── logging_setup.py # Logging utilities
│       └── image.py        # Image processing
├── scripts/
│   └── setup_trellis.sh    # TRELLIS setup script
├── config.yaml             # Default configuration
└── pyproject.toml          # Package metadata
```

## Credits

This tool is built on top of:

- [TRELLIS](https://github.com/microsoft/TRELLIS) by Microsoft Research
- [Trimesh](https://github.com/mikedh/trimesh) for mesh processing
- [Click](https://click.palletsprojects.com/) for CLI
- [Rich](https://github.com/Textualize/rich) for terminal UI

## License

MIT License - See LICENSE file for details

TRELLIS is licensed under MIT by Microsoft. See the [TRELLIS repository](https://github.com/microsoft/TRELLIS) for more details.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions:

- **Tool Issues**: [GitHub Issues](https://github.com/yourusername/trellis-local-tool/issues)
- **TRELLIS Issues**: [TRELLIS GitHub](https://github.com/microsoft/TRELLIS/issues)

## Cloud API (Modal)

For production deployments without managing infrastructure, use the **Modal serverless API**:

- **GPU-accelerated** - A10G with 24GB VRAM
- **Sync & Async endpoints** - Block for immediate results or poll for status
- **Webhook callbacks** - Get notified when jobs complete
- **Auto-scaling** - Scales to zero when idle, handles bursts automatically

See [`api/MODAL_DEPLOYMENT.md`](api/MODAL_DEPLOYMENT.md) for full documentation.

### Quick Example with Callbacks

```bash
# Submit async job with callback
curl -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -F "files=@image.png" \
  "https://your-app.modal.run/api/v1/trellis/async/?callback_url=https://your-server.com/webhook"

# Your webhook receives:
# {
#   "job_id": "...",
#   "status": "completed",
#   "download_url": "https://your-app.modal.run/api/v1/jobs/.../result"
# }
```

## Roadmap

- [x] REST API server mode (Modal cloud deployment)
- [ ] Web interface option
- [ ] Docker containerization
- [ ] Batch resume capability
- [ ] Video frame extraction
- [ ] Multi-GPU support
- [ ] Cloud integration (S3, GCS)

## Changelog

### v0.1.0 (2024-02-09)

- Initial release
- Single image and batch conversion
- GLB export with optimization
- Configuration system
- Progress tracking
- Rich CLI interface
