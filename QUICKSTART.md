# Quick Start Guide

Get up and running with TRELLIS Local Tool in 5 minutes!

## Prerequisites Check

Before starting, ensure you have:

- ✅ NVIDIA GPU with ≥16GB VRAM
- ✅ Linux (or WSL2 on Windows)
- ✅ Python 3.8+
- ✅ CUDA 11.8 or 12.2
- ✅ ~10GB free disk space

Check your GPU:
```bash
nvidia-smi
```

## Installation (3 Steps)

### Step 1: Clone and Setup TRELLIS

```bash
git clone https://github.com/yourusername/trellis-local-tool.git
cd trellis-local-tool
./scripts/setup_trellis.sh
```

### Step 2: Install the Tool

```bash
pip install -e .
```

### Step 3: Download the Model

```bash
trellis-tool setup
```

## First Conversion

Convert your first image:

```bash
# Download a test image (or use your own)
curl -o test.jpg "https://images.unsplash.com/photo-1505664194779-8beaceb93744?w=1024"

# Convert to 3D
trellis-tool convert test.jpg

# Output will be at: ./output/test.glb
```

## View Your 3D Model

Open the GLB file in:

- **Online**: [gltf-viewer.donmccurdy.com](https://gltf-viewer.donmccurdy.com)
- **Blender**: File → Import → glTF 2.0
- **Three.js**: Use GLTFLoader
- **Unity**: Import as asset
- **Windows**: 3D Viewer app

## Common Commands

```bash
# Single image with options
trellis-tool convert image.jpg --texture-size 2048 --optimize

# Batch convert folder
trellis-tool batch ./photos/ --output-dir ./models/

# Get image info
trellis-tool info image.jpg

# Show current config
trellis-tool config-show
```

## Next Steps

- 📖 Read the full [README.md](README.md) for all features
- 🔧 Customize [config.yaml](config.yaml) for your needs
- 💡 Check [examples](examples/README.md) for advanced usage
- 📚 Review [INSTALL.md](INSTALL.md) for troubleshooting

## Tips for Best Results

1. **Image Quality**: Use clear, well-lit photos with minimal background
2. **Resolution**: 1024x1024 or higher works best
3. **Subject**: Single prominent object gives best results
4. **Start Small**: Test with low-res images first
5. **GPU Memory**: Monitor with `nvidia-smi` while processing

## Common Issues

### "CUDA out of memory"
```bash
trellis-tool convert image.jpg --texture-size 1024
```

### "Model not found"
```bash
trellis-tool setup --model microsoft/TRELLIS-image-large
```

### "TRELLIS module not found"
```bash
./scripts/setup_trellis.sh
```

## Performance Tips

- **Fastest**: `--texture-size 1024 --optimize --target-faces 50000`
- **Balanced**: `--texture-size 2048 --optimize` (default)
- **Best Quality**: `--texture-size 4096 --no-optimize`

## Example Workflow

```bash
# 1. Batch convert photos
trellis-tool batch ./vacation_photos/ -r -o ./3d_models/

# 2. Generate variants with different seeds
for seed in 1 2 3; do
    trellis-tool convert car.jpg -o "car_v${seed}.glb" --seed $seed
done

# 3. High-quality single conversion
trellis-tool convert portrait.jpg \
    --texture-size 4096 \
    --no-optimize \
    --output portrait_hq.glb
```

## Getting Help

```bash
# General help
trellis-tool --help

# Command-specific help
trellis-tool convert --help
trellis-tool batch --help
```

## Resources

- **TRELLIS Paper**: [arxiv.org/abs/TRELLIS](https://arxiv.org)
- **TRELLIS Repo**: [github.com/microsoft/TRELLIS](https://github.com/microsoft/TRELLIS)
- **GLB Viewer**: [gltf-viewer.donmccurdy.com](https://gltf-viewer.donmccurdy.com)
- **Test Images**: [unsplash.com](https://unsplash.com)

---

🎉 **You're all set!** Start converting images to 3D models with TRELLIS!
