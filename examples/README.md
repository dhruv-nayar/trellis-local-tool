# Examples

This directory contains example images and usage scripts for the TRELLIS Local Tool.

## Example Images

Add your test images here to try out the tool. Supported formats:
- JPEG/JPG
- PNG
- WebP
- BMP
- TIFF

## Example Usage

### Single Image Conversion

```bash
# Basic conversion
trellis-tool convert examples/chair.jpg

# High quality
trellis-tool convert examples/car.jpg --texture-size 4096
```

### Batch Processing

```bash
# Convert all images in this directory
trellis-tool batch examples/ --output-dir ./outputs/

# Recursive search
trellis-tool batch examples/ -r
```

## Sample Scripts

### batch_convert.sh

```bash
#!/bin/bash
# Convert all images with custom settings

for img in examples/*.jpg; do
    echo "Processing: $img"
    trellis-tool convert "$img" \
        --output "outputs/$(basename "$img" .jpg).glb" \
        --texture-size 2048 \
        --optimize \
        --seed 42
done
```

### process_with_variants.sh

```bash
#!/bin/bash
# Generate multiple variants with different seeds

IMAGE="examples/object.jpg"

for seed in 1 2 3 4 5; do
    echo "Generating variant with seed: $seed"
    trellis-tool convert "$IMAGE" \
        --output "outputs/object_seed${seed}.glb" \
        --seed $seed
done
```

## Python Script Examples

### simple_conversion.py

```python
"""Simple image to GLB conversion."""

from pathlib import Path
from trellis_tool.core.pipeline import TRELLISPipeline

# Create pipeline
pipeline = TRELLISPipeline(
    model_name="microsoft/TRELLIS-image-large",
    device="cuda",
    seed=1,
    texture_size=2048,
    optimize=True
)

# Setup (loads model)
pipeline.setup()

# Convert image
result = pipeline.process_image(
    image_path=Path("examples/input.jpg"),
    output_path=Path("outputs/model.glb")
)

print(f"Generated: {result}")
```

### batch_with_config.py

```python
"""Batch processing with custom configuration."""

from pathlib import Path
from trellis_tool.core.pipeline import TRELLISPipeline
from trellis_tool.utils.image import find_images

# Find all images
images = find_images(Path("examples"), recursive=True)
print(f"Found {len(images)} images")

# Create pipeline with custom settings
pipeline = TRELLISPipeline(
    model_name="microsoft/TRELLIS-image-large",
    device="cuda",
    seed=42,
    texture_size=2048,
    optimize=True,
    target_faces=100000  # Optimize to 100k faces
)

# Process batch
results = pipeline.process_batch(
    image_paths=images,
    output_dir=Path("outputs"),
    naming_pattern="{name}_{seed}"
)

print(f"Successfully converted: {len(results)} images")
```

### advanced_processing.py

```python
"""Advanced processing with error handling and logging."""

import logging
from pathlib import Path
from trellis_tool.core.pipeline import TRELLISPipeline
from trellis_tool.utils.logging_setup import setup_logging
from trellis_tool.utils.image import find_images, validate_image

# Setup logging
setup_logging(level="INFO", log_file=Path("conversion.log"))
logger = logging.getLogger(__name__)

# Configuration
INPUT_DIR = Path("examples")
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Find and validate images
images = find_images(INPUT_DIR, recursive=True)
valid_images = [img for img in images if validate_image(img)]

logger.info(f"Found {len(valid_images)} valid images")

# Create pipeline
pipeline = TRELLISPipeline(
    model_name="microsoft/TRELLIS-image-large",
    device="auto",
    seed=1
)

# Process with error handling
results = []
for i, image in enumerate(valid_images, 1):
    try:
        logger.info(f"[{i}/{len(valid_images)}] Processing: {image.name}")

        output_path = OUTPUT_DIR / f"{image.stem}.glb"
        result = pipeline.process_image(image, output_path)

        results.append(result)
        logger.info(f"Success: {result}")

    except Exception as e:
        logger.error(f"Failed to process {image.name}: {e}")
        continue

# Summary
logger.info(f"Completed: {len(results)}/{len(valid_images)} successful")
```

## Tips

1. **Start Small**: Test with a single low-resolution image first
2. **GPU Memory**: Monitor GPU memory with `nvidia-smi`
3. **Quality vs Speed**: Lower texture sizes are faster but less detailed
4. **Optimization**: Enable optimization for web/mobile use cases
5. **Seeds**: Use fixed seeds for reproducible results

## Getting Test Images

You can download free test images from:
- [Unsplash](https://unsplash.com) - High-quality photos
- [Pexels](https://pexels.com) - Free stock photos
- [Pixabay](https://pixabay.com) - Public domain images

Best results with:
- Clear, well-lit objects
- Minimal background clutter
- Single prominent subject
- High resolution (1024x1024 or higher)
