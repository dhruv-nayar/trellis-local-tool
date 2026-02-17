# TRELLIS API - Modal Deployment

Serverless deployment of TRELLIS API on [Modal](https://modal.com) with GPU support.

## Getting an API Key

To use this API, you need an API key. Contact the API owner to request access:

- **Email**: [your-email@example.com]
- **GitHub Issues**: [Open an issue](https://github.com/dhruv-nayar/trellis-local-tool/issues) requesting API access

Once you have a key, include it in all requests:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" ...
```

## Live Endpoints

Once deployed, your API will be available at:
- **Base URL**: `https://<your-username>--trellis-api-fastapi-app.modal.run`
- **Swagger Docs**: `https://<your-username>--trellis-api-fastapi-app.modal.run/docs`

## Features

- **GPU-Accelerated TRELLIS**: Runs on NVIDIA A10G (24GB VRAM)
- **CPU-Based RemBG**: Lightweight background removal
- **Serverless**: Auto-scales to zero when not in use
- **Model Caching**: ~5GB TRELLIS model cached on Modal Volume
- **No Infrastructure Management**: Modal handles everything

## Quick Start

### Prerequisites

1. Create a [Modal account](https://modal.com)
2. Install Modal CLI:
   ```bash
   pip install modal
   ```
3. Authenticate:
   ```bash
   modal token new
   ```

### Set Up API Keys

Before deploying, create a Modal secret with your API keys:

```bash
modal secret create trellis-api-keys API_KEYS="your-key-1,your-key-2,your-key-3"
```

You can add multiple comma-separated keys. To update keys later:

```bash
modal secret create trellis-api-keys API_KEYS="new-key-1,new-key-2" --force
```

### Deploy

```bash
cd api
modal deploy modal_app.py
```

You'll see output like:
```
✓ Created web function fastapi_app => https://your-username--trellis-api-fastapi-app.modal.run
```

### Local Testing

```bash
modal serve modal_app.py
```

This runs the app locally with a temporary URL for testing.

## API Reference

### Health Check

```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "2.1.0-modal-gpu"
}
```

### Background Removal (RemBG)

Remove background from images using the u2net model.

```bash
POST /api/v1/rembg/
Content-Type: multipart/form-data
```

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| files | File | Image file (JPG, PNG, WebP) |

**Response:** PNG image with transparent background

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer your-api-key" \
  -F "files=@input.jpg" \
  https://your-username--trellis-api-fastapi-app.modal.run/api/v1/rembg/ \
  --output output_nobg.png
```

### Image to 3D (TRELLIS)

Convert an image to a 3D GLB model using Microsoft's TRELLIS.

```bash
POST /api/v1/trellis/
Content-Type: multipart/form-data
Authorization: Bearer your-api-key
```

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| files | File | required | Image file (PNG with transparency recommended) |
| seed | int | 0 | Random seed for reproducibility |

**Response:** GLB binary file (model/gltf-binary)

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer your-api-key" \
  -F "files=@object.png" \
  https://your-username--trellis-api-fastapi-app.modal.run/api/v1/trellis/ \
  --output model.glb
```

## Usage Examples

### Complete Workflow: Image to 3D

For best results, first remove the background, then convert to 3D:

```bash
# Set your API key
export TRELLIS_API_KEY="your-api-key"

# Step 1: Remove background
curl -X POST \
  -H "Authorization: Bearer $TRELLIS_API_KEY" \
  -F "files=@photo.jpg" \
  https://your-username--trellis-api-fastapi-app.modal.run/api/v1/rembg/ \
  --output photo_nobg.png

# Step 2: Convert to 3D
curl -X POST \
  -H "Authorization: Bearer $TRELLIS_API_KEY" \
  -F "files=@photo_nobg.png" \
  https://your-username--trellis-api-fastapi-app.modal.run/api/v1/trellis/ \
  --output model.glb
```

### Python Client

```python
import requests

BASE_URL = "https://your-username--trellis-api-fastapi-app.modal.run"
API_KEY = "your-api-key"

HEADERS = {"Authorization": f"Bearer {API_KEY}"}

def remove_background(image_path: str, output_path: str):
    """Remove background from an image."""
    with open(image_path, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/api/v1/rembg/",
            headers=HEADERS,
            files={"files": f}
        )
    response.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(response.content)
    print(f"Saved: {output_path}")

def image_to_3d(image_path: str, output_path: str, seed: int = 0):
    """Convert image to 3D GLB model."""
    with open(image_path, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/api/v1/trellis/",
            headers=HEADERS,
            files={"files": f},
            data={"seed": seed}
        )
    response.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(response.content)
    print(f"Saved: {output_path}")

# Usage
remove_background("photo.jpg", "photo_nobg.png")
image_to_3d("photo_nobg.png", "model.glb", seed=42)
```

### JavaScript/TypeScript

```typescript
const BASE_URL = "https://your-username--trellis-api-fastapi-app.modal.run";
const API_KEY = "your-api-key";

async function removeBackground(imageFile: File): Promise<Blob> {
  const formData = new FormData();
  formData.append("files", imageFile);

  const response = await fetch(`${BASE_URL}/api/v1/rembg/`, {
    method: "POST",
    headers: { "Authorization": `Bearer ${API_KEY}` },
    body: formData,
  });

  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.blob();
}

async function imageToGlb(imageFile: File, seed = 0): Promise<Blob> {
  const formData = new FormData();
  formData.append("files", imageFile);
  formData.append("seed", seed.toString());

  const response = await fetch(`${BASE_URL}/api/v1/trellis/`, {
    method: "POST",
    headers: { "Authorization": `Bearer ${API_KEY}` },
    body: formData,
  });

  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.blob();
}

// Usage
const imageInput = document.querySelector<HTMLInputElement>("#image-input");
imageInput?.addEventListener("change", async (e) => {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;

  // Remove background first
  const nobgBlob = await removeBackground(file);
  const nobgFile = new File([nobgBlob], "nobg.png", { type: "image/png" });

  // Convert to 3D
  const glbBlob = await imageToGlb(nobgFile);

  // Download
  const url = URL.createObjectURL(glbBlob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "model.glb";
  a.click();
});
```

## API Key Management

### Creating Keys

API keys are stored as a Modal secret. Create or update keys:

```bash
# Create initial keys
modal secret create trellis-api-keys API_KEYS="key1,key2,key3"

# Update keys (use --force to overwrite)
modal secret create trellis-api-keys API_KEYS="new-key1,new-key2" --force
```

### Key Format

- Keys are comma-separated
- No spaces around commas
- Keys can be any string (recommend UUID or secure random strings)

**Generating secure keys:**
```bash
# Generate a secure random key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Or use uuidgen
uuidgen
```

### Distributing Keys

Give users their API key and the endpoint URL:

```
API Endpoint: https://your-username--trellis-api-fastapi-app.modal.run
API Key: their-unique-key

Usage:
curl -X POST \
  -H "Authorization: Bearer their-unique-key" \
  -F "files=@image.png" \
  https://your-username--trellis-api-fastapi-app.modal.run/api/v1/trellis/ \
  -o model.glb
```

### Revoking Keys

To revoke a key, update the secret without that key:

```bash
# Remove "compromised-key" from the list
modal secret create trellis-api-keys API_KEYS="valid-key1,valid-key2" --force
```

Then redeploy:
```bash
modal deploy modal_app.py
```

## Performance

### Cold Start Times

| Endpoint | Cold Start | Warm Request |
|----------|------------|--------------|
| RemBG | ~5-10s | ~2-5s |
| TRELLIS (first run) | ~2-3 min | ~30-60s |
| TRELLIS (model cached) | ~30-60s | ~30-60s |

**Note:** First TRELLIS request downloads the ~5GB model, which is then cached on a Modal Volume.

### GPU Configuration

The TRELLIS endpoint runs on:
- **GPU**: NVIDIA A10G (24GB VRAM)
- **Timeout**: 10 minutes
- **Model**: TRELLIS-image-large (1.2B parameters)

## Best Practices

### Image Requirements

For optimal 3D conversion:
1. **Use transparent backgrounds** - Run through `/api/v1/rembg/` first
2. **Single object** - One clear subject per image
3. **Good lighting** - Well-lit, minimal shadows
4. **Multiple angles** - If possible, use images showing object structure

### Error Handling

```python
import requests

def convert_with_retry(image_path: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            with open(image_path, "rb") as f:
                response = requests.post(
                    f"{BASE_URL}/api/v1/trellis/",
                    files={"files": f},
                    timeout=600  # 10 minute timeout
                )
            response.raise_for_status()
            return response.content
        except requests.exceptions.Timeout:
            print(f"Attempt {attempt + 1} timed out, retrying...")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 500:
                print(f"Server error: {e.response.text}")
            raise
    raise Exception("Max retries exceeded")
```

## Monitoring

### Modal Dashboard

View logs, metrics, and function invocations at:
https://modal.com/apps/your-username/main/deployed/trellis-api

### Check Logs

```bash
modal app logs trellis-api
```

## Cost Estimation

Modal pricing (as of 2024):
- **CPU (RemBG)**: ~$0.000025/second
- **A10G GPU (TRELLIS)**: ~$0.000583/second

Estimated costs per request:
- RemBG: ~$0.0001 (3-5 seconds)
- TRELLIS: ~$0.02-0.05 (30-60 seconds)

## Troubleshooting

### "zero-size array" Error

**Cause:** Empty mesh generated - usually due to unsuitable input image.

**Solution:**
- Use an image with a clear object
- Remove background first with `/api/v1/rembg/`
- Avoid solid colors or abstract images

### Timeout Errors

**Cause:** First request downloads the 5GB model.

**Solution:**
- Increase client timeout to 10+ minutes for first request
- Subsequent requests will be faster (model cached)

### Volume Mount Errors

**Cause:** Docker image conflicts with Modal volume.

**Solution:** Already fixed in current code. If you see this, ensure you're using the latest `modal_app.py`.

### GPU Not Available

**Cause:** Modal GPU quota or availability.

**Solution:**
- Check Modal dashboard for GPU availability
- Try a different GPU type (edit `modal_app.py`):
  ```python
  @app.function(gpu="T4")  # or "A100", "L4"
  ```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Modal Platform                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐    ┌────────────────────────────┐ │
│  │  FastAPI App     │    │  TRELLIS GPU Function      │ │
│  │  (CPU, rembg)    │───▶│  (A10G, 24GB VRAM)         │ │
│  │                  │    │                            │ │
│  │  /api/v1/rembg/  │    │  - Model loading           │ │
│  │  /api/v1/trellis/│    │  - Inference               │ │
│  │  /health         │    │  - Mesh extraction         │ │
│  └──────────────────┘    └────────────────────────────┘ │
│           │                          │                   │
│           ▼                          ▼                   │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Modal Volume                         │   │
│  │  /model_cache/huggingface  (HF models)           │   │
│  │  /model_cache/torch        (PyTorch hub)         │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Development

### Modify GPU Function

Edit the inference logic in `modal_app.py`:

```python
@app.function(
    image=trellis_gpu_image,
    gpu="A10G",
    timeout=600,
    volumes={"/model_cache": model_volume},
)
def trellis_gpu_inference(image_bytes: bytes, seed: int = 0, texture_size: int = 1024) -> bytes:
    # Your custom logic here
    ...
```

### Add New Endpoints

Add routes inside the `fastapi_app()` function:

```python
@fastapi.post("/api/v1/custom/")
async def custom_endpoint(files: list[UploadFile] = File(...)):
    # Your logic
    return {"result": "success"}
```

### Testing Changes

```bash
# Test locally before deploying
modal serve modal_app.py

# Deploy when ready
modal deploy modal_app.py
```

## Related Documentation

- [Modal Documentation](https://modal.com/docs)
- [TRELLIS GitHub](https://github.com/microsoft/TRELLIS)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [RemBG Documentation](https://github.com/danielgatis/rembg)
