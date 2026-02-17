"""
TRELLIS API - Modal Deployment with Self-Hosted GPU

Deploy with:
    modal deploy modal_app.py

Test locally:
    modal serve modal_app.py
"""

import modal

# Define the Modal app
app = modal.App("trellis-api")

# Volume for caching the TRELLIS model (~5GB)
model_volume = modal.Volume.from_name("trellis-model-cache", create_if_missing=True)

# ============================================================================
# Image for RemBG (CPU-only, lightweight)
# ============================================================================
rembg_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "libgl1",
        "libglib2.0-0",
        "libsm6",
        "libxext6",
        "libxrender1",
    )
    .pip_install(
        "fastapi>=0.109.0",
        "uvicorn[standard]>=0.27.0",
        "python-multipart>=0.0.6",
        "pydantic>=2.0.0",
        "pillow>=9.0.0",
        "rembg[cpu]>=2.0.50",
        "onnxruntime>=1.16.0",
    )
)

# ============================================================================
# Image for TRELLIS (GPU, with all ML dependencies)
# Uses pre-built Docker image with all CUDA extensions compiled
# Source: https://hub.docker.com/r/samueltagliabracci/trellis3d-ubuntu22
# ============================================================================
trellis_gpu_image = (
    modal.Image.from_registry(
        "samueltagliabracci/trellis3d-ubuntu22:latest",
        add_python=None,  # Image already has Python via conda
    )
    .env({
        "HF_HOME": "/model_cache/huggingface",
        "TORCH_HOME": "/model_cache/torch",
        "ATTN_BACKEND": "xformers",
        "SPCONV_ALGO": "native",
        # Ensure conda environment is activated
        "PATH": "/root/miniconda3/envs/trellis/bin:/root/miniconda3/bin:$PATH",
        "CONDA_DEFAULT_ENV": "trellis",
    })
    # Install trimesh for GLB export
    .run_commands([
        "/opt/conda/envs/trellis/bin/pip install trimesh",
    ])
)


# ============================================================================
# TRELLIS GPU Inference Function
# ============================================================================
@app.function(
    image=trellis_gpu_image,
    gpu="A10G",  # 24GB VRAM - good for TRELLIS
    timeout=600,  # 10 minutes
    volumes={"/model_cache": model_volume},
)
def trellis_gpu_inference(image_bytes: bytes, seed: int = 0, texture_size: int = 1024) -> bytes:
    """Run TRELLIS inference on GPU and return GLB bytes."""
    import os

    # Set cache directories (using /model_cache which is mounted as a Modal volume)
    os.environ["HF_HOME"] = "/model_cache/huggingface"
    os.environ["TORCH_HOME"] = "/model_cache/torch"
    os.makedirs("/model_cache/huggingface", exist_ok=True)
    os.makedirs("/model_cache/torch", exist_ok=True)

    import torch
    from PIL import Image
    import io
    import trimesh
    import numpy as np

    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA device: {torch.cuda.get_device_name(0)}")

    print("Loading TRELLIS model... (first run downloads ~5GB)")

    # Load model
    from trellis.pipelines import TrellisImageTo3DPipeline

    pipeline = TrellisImageTo3DPipeline.from_pretrained(
        "JeffreyXiang/TRELLIS-image-large",
    )
    pipeline.cuda()

    print("Model loaded, processing image...")

    # Load input image
    image = Image.open(io.BytesIO(image_bytes))
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    # Set seed for reproducibility
    torch.manual_seed(seed)

    # Run inference
    outputs = pipeline.run(
        image,
        seed=seed,
        formats=["gaussian", "mesh"],
        preprocess_image=True,
    )

    print("Inference complete, extracting mesh...")

    # Get mesh data from outputs
    mesh_result = outputs["mesh"][0]

    # Extract vertices and faces from the mesh result
    vertices = mesh_result.vertices.cpu().numpy()
    faces = mesh_result.faces.cpu().numpy()

    print(f"Mesh: {len(vertices)} vertices, {len(faces)} faces")

    # Get vertex colors if available
    vertex_colors = None
    if hasattr(mesh_result, 'vertex_attrs') and mesh_result.vertex_attrs is not None:
        attrs = mesh_result.vertex_attrs
        if isinstance(attrs, torch.Tensor):
            # Assuming vertex_attrs contains colors in some format
            attrs_np = attrs.cpu().numpy()
            if attrs_np.shape[-1] >= 3:
                # Take first 3 channels as RGB
                vertex_colors = attrs_np[..., :3]
                # Normalize to 0-255 if needed
                if vertex_colors.max() <= 1.0:
                    vertex_colors = (vertex_colors * 255).astype(np.uint8)

    # Create trimesh object
    mesh = trimesh.Trimesh(
        vertices=vertices,
        faces=faces,
        vertex_colors=vertex_colors,
    )

    print("Exporting to GLB...")

    # Export to GLB bytes
    glb_bytes = mesh.export(file_type='glb')

    print(f"GLB exported, size: {len(glb_bytes)} bytes")

    # Commit volume changes to cache model
    model_volume.commit()

    # Cleanup GPU memory
    del pipeline
    torch.cuda.empty_cache()

    return glb_bytes


# ============================================================================
# FastAPI Application
# ============================================================================
@app.function(
    image=rembg_image,
    timeout=600,
)
@modal.asgi_app()
def fastapi_app():
    """Serve the FastAPI application."""
    from fastapi import FastAPI, UploadFile, File, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import Response
    from pathlib import Path

    fastapi = FastAPI(
        title="TRELLIS API (Modal)",
        version="2.1.0-modal-gpu",
    )

    fastapi.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @fastapi.get("/")
    def root():
        return {
            "name": "TRELLIS API (Modal)",
            "version": "2.1.0-modal-gpu",
            "endpoints": {
                "health": "/health",
                "rembg": "/api/v1/rembg/",
                "trellis": "/api/v1/trellis/",
            },
            "info": {
                "trellis": "Self-hosted on Modal GPU (A10G, 24GB VRAM)",
                "rembg": "CPU-based background removal",
            }
        }

    @fastapi.get("/health")
    def health():
        return {"status": "healthy", "version": "2.1.0-modal-gpu"}

    @fastapi.post("/api/v1/rembg/")
    async def remove_background(files: list[UploadFile] = File(...)):
        """Remove background from images"""
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        # Lazy import rembg only when needed
        from rembg import remove, new_session
        from PIL import Image
        import io

        # Process first file
        file = files[0]
        content = await file.read()

        # Process image
        img = Image.open(io.BytesIO(content))
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        session = new_session("u2net")
        output = remove(img, session=session)

        # Convert to bytes
        output_buffer = io.BytesIO()
        output.save(output_buffer, format="PNG")
        output_buffer.seek(0)

        return Response(
            content=output_buffer.getvalue(),
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{Path(file.filename).stem}_nobg.png"'}
        )

    @fastapi.post("/api/v1/trellis/")
    async def image_to_3d(
        files: list[UploadFile] = File(...),
        seed: int = 0,
    ):
        """Convert image to 3D GLB model using self-hosted TRELLIS on GPU"""
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        file = files[0]
        image_bytes = await file.read()

        try:
            # Call the GPU function
            glb_bytes = trellis_gpu_inference.remote(
                image_bytes=image_bytes,
                seed=seed,
                texture_size=1024,
            )

            return Response(
                content=glb_bytes,
                media_type="model/gltf-binary",
                headers={
                    "Content-Disposition": f'attachment; filename="{Path(file.filename).stem}.glb"'
                }
            )
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            raise HTTPException(status_code=500, detail=f"TRELLIS processing failed: {str(e)}\n{tb[:500]}")

    return fastapi


# For local testing with `modal serve`
if __name__ == "__main__":
    print("Run with: modal serve modal_app.py")
    print("Or deploy with: modal deploy modal_app.py")
