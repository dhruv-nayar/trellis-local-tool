# Google Colab Quick Start Guide

Since you're on macOS with Apple Silicon (no NVIDIA GPU), the easiest way to use TRELLIS is through Google Colab.

## 🚀 Steps to Get Started

### 1. Upload the Notebook to Colab

**Option A: Direct Upload**
1. Go to [Google Colab](https://colab.research.google.com)
2. Click **File** → **Upload notebook**
3. Upload the file: `TRELLIS_Image_to_3D.ipynb` from this project

**Option B: Upload to Google Drive First**
1. Upload `TRELLIS_Image_to_3D.ipynb` to your Google Drive
2. Right-click the file → **Open with** → **Google Colaboratory**

**Option C: Use GitHub** (if you push this to GitHub)
1. Go to [Google Colab](https://colab.research.google.com)
2. Click **File** → **Open notebook** → **GitHub** tab
3. Enter your repo URL

### 2. Enable GPU

⚠️ **This is crucial!**

1. In Colab, go to **Runtime** → **Change runtime type**
2. Under **Hardware accelerator**, select **T4 GPU**
3. Click **Save**

### 3. Run the Notebook

Run each cell in order (click the play button or press `Shift+Enter`):

1. **Cell 1**: Check GPU - Verify you see GPU info
2. **Cell 2**: Install dependencies (5-10 minutes first time)
3. **Cell 3**: Load model (downloads ~5GB, one-time)
4. **Cell 4**: Load helper functions
5. **Cell 5**: Upload your images
6. **Cell 6**: Convert single image
7. **Cell 7-8**: Optional batch processing and download

### 4. Convert Your First Image

After running cells 1-5:

```python
# In Cell 6, update the IMAGE_PATH to your uploaded image:
IMAGE_PATH = "/content/inputs/your-image.jpg"  # Change filename here
OUTPUT_PATH = "/content/output.glb"
SEED = 1

# Then run the cell
```

### 5. Download Your 3D Model

After conversion completes, click the download link that appears, or run Cell 8 to download all models as a zip.

## 📊 What to Expect

### Free Tier (T4 GPU)
- **Processing Time**: ~30-60 seconds per image
- **Max Session**: ~2-3 hours of continuous use
- **GPU Memory**: 15GB (enough for most images)
- **Cost**: FREE! ✨

### Colab Pro ($10/month)
- **Better GPU**: A100 or V100 options
- **Faster**: ~20-30 seconds per image
- **Longer Sessions**: Up to 24 hours
- **Priority**: Skip wait times

## 💡 Tips for Best Results

### Image Selection
✅ **Good:**
- Clear, well-lit objects
- Single prominent subject
- Minimal background clutter
- High resolution (1024x1024+)
- Objects with good depth/shape

❌ **Avoid:**
- Flat 2D images
- Very cluttered scenes
- Poor lighting
- Extremely low resolution

### Example Good Subjects
- Furniture (chairs, tables, lamps)
- Vehicles (cars, bikes, boats)
- Products (shoes, bottles, gadgets)
- Characters/figurines
- Food items
- Plants/flowers

## 🔧 Troubleshooting

### "No GPU available"
- Go to **Runtime** → **Change runtime type** → Select **T4 GPU**
- If unavailable, you might need to wait or try Colab Pro

### "Out of Memory"
- Restart runtime: **Runtime** → **Restart runtime**
- Process one image at a time
- Use smaller images (resize to 1024x1024)

### "Model download failed"
- Check internet connection
- Restart runtime and try again
- Model is ~5GB, takes a few minutes

### "Export failed"
- Check the debug output in the cell
- The TRELLIS API might have changed
- Try restarting and re-running from the beginning

### Session Disconnected
- Free tier has time limits
- Run all cells again from the start
- Models stay cached, so it's faster second time

## 📱 Using on Mobile

You can run Colab notebooks on mobile!

1. Open Colab in mobile browser
2. Upload images from phone camera
3. Let it process
4. Download GLB files
5. View in mobile 3D viewer apps

## 🎯 Quick Workflow

```
1. Open Colab notebook
2. Enable T4 GPU
3. Run cells 1-4 (one-time setup)
4. Upload images (cell 5)
5. Convert (cell 6)
6. Download GLB
7. View in 3D viewer
```

## 🌐 View Your Models Online

After downloading your GLB file:

1. Go to [gltf-viewer.donmccurdy.com](https://gltf-viewer.donmccurdy.com)
2. Drag and drop your GLB file
3. Rotate, zoom, inspect your 3D model!

Or use:
- [Sketchfab](https://sketchfab.com) - Upload and share
- [Three.js Editor](https://threejs.org/editor/)
- [Babylon.js Sandbox](https://sandbox.babylonjs.com)

## 💰 Cost Comparison

| Service | GPU | Speed | Cost | Notes |
|---------|-----|-------|------|-------|
| Colab Free | T4 | 30-60s | FREE | Best for testing |
| Colab Pro | A100 | 20-30s | $10/mo | Better for batches |
| RunPod | A6000 | 15-25s | $0.79/hr | Pay per use |
| Local (if you had GPU) | Your GPU | Varies | HW cost | No cloud limits |

## 🎓 Next Steps

After you get comfortable:

1. **Batch Processing**: Convert multiple images at once (Cell 7)
2. **Experiment with Seeds**: Different seeds = different results
3. **Try Different Images**: See what works best
4. **Share Models**: Upload to Sketchfab or your portfolio
5. **Use in Projects**: Import GLB into Unity, Blender, Three.js

## 📝 Notes

- **Session Persistence**: Uploaded files and outputs are deleted when you close Colab
- **Save Your Work**: Download GLB files before ending session
- **Model Cache**: Model is cached, so subsequent runs are much faster
- **GPU Limits**: Free tier has usage limits, spread out heavy processing

## 🆘 Need Help?

1. Check error messages in the notebook output
2. Review the troubleshooting section above
3. Consult [TRELLIS GitHub Issues](https://github.com/microsoft/TRELLIS/issues)
4. Ask in relevant communities (Reddit, Discord)

---

**Have fun creating 3D models from your images! 🎨✨**
