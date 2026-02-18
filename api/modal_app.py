"""
TRELLIS API - Modal Deployment with Self-Hosted GPU

Deploy with:
    modal deploy modal_app.py

Test locally:
    modal serve modal_app.py

Set API keys:
    modal secret create trellis-api-keys API_KEYS="key1,key2,key3"
"""

import modal
import os

# Define the Modal app
app = modal.App("trellis-api")

# Secret for API keys (comma-separated list)
api_keys_secret = modal.Secret.from_name("trellis-api-keys", required_keys=["API_KEYS"])

# Volume for caching the TRELLIS model (~5GB)
model_volume = modal.Volume.from_name("trellis-model-cache", create_if_missing=True)

# Volume for storing async job results (GLB, PNG files)
results_volume = modal.Volume.from_name("trellis-job-results", create_if_missing=True)

# Dict for storing async job state
job_dict = modal.Dict.from_name("trellis-jobs", create_if_missing=True)

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
        "requests>=2.28.0",  # For callback webhooks
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
    # Install trimesh for GLB export and requests for callbacks
    .run_commands([
        "/opt/conda/envs/trellis/bin/pip install trimesh requests",
    ])
)


# ============================================================================
# Job State Management (for async endpoints)
# ============================================================================
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
import json


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    TRELLIS = "trellis"
    REMBG = "rembg"


def send_callback(callback_url: str, job_data: Dict[str, Any], base_url: str = "") -> bool:
    """Send job status to callback URL. Returns True if successful."""
    import requests

    if not callback_url:
        return False

    try:
        # Build callback payload
        payload = {
            "job_id": job_data["job_id"],
            "status": job_data["status"],
            "job_type": job_data["job_type"],
            "created_at": job_data["created_at"],
            "completed_at": job_data.get("completed_at"),
            "progress": job_data.get("progress", 0),
            "message": job_data.get("message"),
            "error": job_data.get("error"),
            "output_size_bytes": job_data.get("output_size_bytes"),
        }

        # Add download URL if completed
        if job_data["status"] == "completed" and job_data.get("output_filename"):
            payload["download_url"] = f"{base_url}/api/v1/jobs/{job_data['job_id']}/result"

        print(f"[Job {job_data['job_id']}] Sending callback to {callback_url}")

        response = requests.post(
            callback_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        print(f"[Job {job_data['job_id']}] Callback response: {response.status_code}")
        return response.status_code < 400

    except Exception as e:
        print(f"[Job {job_data['job_id']}] Callback failed: {e}")
        return False


class ModalJobStore:
    """Manages job state in Modal Dict."""

    def __init__(self, modal_dict):
        self.dict = modal_dict

    def create_job(
        self,
        job_id: str,
        job_type: JobType,
        modal_call_id: str,
        input_filename: str,
        **metadata
    ) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat() + "Z"
        job_data = {
            "job_id": job_id,
            "job_type": job_type.value,
            "status": JobStatus.PENDING.value,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
            "progress": 0,
            "message": "Job queued for processing",
            "error": None,
            "modal_call_id": modal_call_id,
            "input_filename": input_filename,
            "output_filename": None,
            "output_size_bytes": None,
            **metadata
        }
        self.dict[job_id] = json.dumps(job_data)
        return job_data

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        try:
            data = self.dict[job_id]
            if data:
                return json.loads(data)
        except KeyError:
            pass
        return None

    def update_job(self, job_id: str, **updates) -> Optional[Dict[str, Any]]:
        job_data = self.get_job(job_id)
        if not job_data:
            return None

        job_data.update(updates)
        job_data["updated_at"] = datetime.utcnow().isoformat() + "Z"

        if updates.get("status") in (JobStatus.COMPLETED.value, JobStatus.FAILED.value):
            job_data["completed_at"] = job_data["updated_at"]

        self.dict[job_id] = json.dumps(job_data)
        return job_data

    def delete_job(self, job_id: str) -> bool:
        try:
            del self.dict[job_id]
            return True
        except KeyError:
            return False


# ============================================================================
# TRELLIS GPU Inference Function (Sync - for existing endpoint)
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
# TRELLIS GPU Inference Function (Async - updates job state)
# ============================================================================
@app.function(
    image=trellis_gpu_image,
    gpu="A10G",
    timeout=600,
    volumes={
        "/model_cache": model_volume,
        "/results": results_volume,
    },
)
def trellis_gpu_inference_async(
    job_id: str,
    image_bytes: bytes,
    seed: int = 0,
    texture_size: int = 1024,
    callback_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Async TRELLIS inference that updates job state and saves to volume."""
    import os

    # Set cache directories
    os.environ["HF_HOME"] = "/model_cache/huggingface"
    os.environ["TORCH_HOME"] = "/model_cache/torch"
    os.makedirs("/model_cache/huggingface", exist_ok=True)
    os.makedirs("/model_cache/torch", exist_ok=True)
    os.makedirs("/results", exist_ok=True)

    import torch
    from PIL import Image
    import io
    import trimesh
    import numpy as np

    # Get job store - must load Dict inside function context
    _job_dict = modal.Dict.from_name("trellis-jobs")
    job_store = ModalJobStore(_job_dict)

    job_store.update_job(
        job_id,
        status=JobStatus.PROCESSING.value,
        progress=10,
        message="Loading TRELLIS model..."
    )

    try:
        print(f"[Job {job_id}] PyTorch version: {torch.__version__}")
        print(f"[Job {job_id}] CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"[Job {job_id}] CUDA device: {torch.cuda.get_device_name(0)}")

        print(f"[Job {job_id}] Loading TRELLIS model...")

        from trellis.pipelines import TrellisImageTo3DPipeline

        pipeline = TrellisImageTo3DPipeline.from_pretrained(
            "JeffreyXiang/TRELLIS-image-large",
        )
        pipeline.cuda()

        job_store.update_job(job_id, progress=30, message="Running inference...")

        # Load input image
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        torch.manual_seed(seed)

        # Run inference
        outputs = pipeline.run(
            image,
            seed=seed,
            formats=["gaussian", "mesh"],
            preprocess_image=True,
        )

        job_store.update_job(job_id, progress=70, message="Extracting mesh...")

        # Get mesh data
        mesh_result = outputs["mesh"][0]
        vertices = mesh_result.vertices.cpu().numpy()
        faces = mesh_result.faces.cpu().numpy()

        print(f"[Job {job_id}] Mesh: {len(vertices)} vertices, {len(faces)} faces")

        # Get vertex colors if available
        vertex_colors = None
        if hasattr(mesh_result, 'vertex_attrs') and mesh_result.vertex_attrs is not None:
            attrs = mesh_result.vertex_attrs
            if isinstance(attrs, torch.Tensor):
                attrs_np = attrs.cpu().numpy()
                if attrs_np.shape[-1] >= 3:
                    vertex_colors = attrs_np[..., :3]
                    if vertex_colors.max() <= 1.0:
                        vertex_colors = (vertex_colors * 255).astype(np.uint8)

        mesh = trimesh.Trimesh(
            vertices=vertices,
            faces=faces,
            vertex_colors=vertex_colors,
        )

        job_store.update_job(job_id, progress=90, message="Saving result...")

        # Export GLB
        glb_bytes = mesh.export(file_type='glb')
        output_filename = f"{job_id}.glb"
        output_path = f"/results/{output_filename}"

        with open(output_path, "wb") as f:
            f.write(glb_bytes)

        print(f"[Job {job_id}] GLB saved: {output_path} ({len(glb_bytes)} bytes)")

        # Commit volume changes
        results_volume.commit()
        model_volume.commit()

        # Mark complete
        job_data = job_store.update_job(
            job_id,
            status=JobStatus.COMPLETED.value,
            progress=100,
            message="Successfully generated 3D model",
            output_filename=output_filename,
            output_size_bytes=len(glb_bytes),
        )

        # Send callback if configured
        if callback_url:
            send_callback(
                callback_url,
                job_data,
                base_url="https://nayardhruv0--trellis-api-fastapi-app.modal.run"
            )

        # Cleanup
        del pipeline
        torch.cuda.empty_cache()

        return {
            "job_id": job_id,
            "status": "completed",
            "output_filename": output_filename,
            "output_size_bytes": len(glb_bytes),
        }

    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()[:500]}"
        print(f"[Job {job_id}] Error: {error_msg}")
        job_data = job_store.update_job(
            job_id,
            status=JobStatus.FAILED.value,
            error=error_msg,
            message="Processing failed",
        )

        # Send callback on failure too
        if callback_url:
            send_callback(
                callback_url,
                job_data,
                base_url="https://nayardhruv0--trellis-api-fastapi-app.modal.run"
            )

        raise


# ============================================================================
# RemBG Async Function (updates job state)
# ============================================================================
@app.function(
    image=rembg_image,
    timeout=300,
    volumes={"/results": results_volume},
)
def rembg_process_async(
    job_id: str,
    image_bytes: bytes,
    model: str = "u2net",
    alpha_matting: bool = False,
    callback_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Async RemBG processing that updates job state and saves to volume."""
    from rembg import remove, new_session
    from PIL import Image
    import io
    import os

    os.makedirs("/results", exist_ok=True)

    # Get job store - must load Dict inside function context
    _job_dict = modal.Dict.from_name("trellis-jobs")
    job_store = ModalJobStore(_job_dict)

    job_store.update_job(
        job_id,
        status=JobStatus.PROCESSING.value,
        progress=20,
        message="Processing image..."
    )

    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        session = new_session(model)
        output = remove(img, session=session, alpha_matting=alpha_matting)

        job_store.update_job(job_id, progress=80, message="Saving result...")

        # Save result
        output_filename = f"{job_id}_nobg.png"
        output_path = f"/results/{output_filename}"

        output_buffer = io.BytesIO()
        output.save(output_buffer, format="PNG")
        output_bytes = output_buffer.getvalue()

        with open(output_path, "wb") as f:
            f.write(output_bytes)

        print(f"[Job {job_id}] PNG saved: {output_path} ({len(output_bytes)} bytes)")

        results_volume.commit()

        job_data = job_store.update_job(
            job_id,
            status=JobStatus.COMPLETED.value,
            progress=100,
            message="Background removed successfully",
            output_filename=output_filename,
            output_size_bytes=len(output_bytes),
        )

        # Send callback if configured
        if callback_url:
            send_callback(
                callback_url,
                job_data,
                base_url="https://nayardhruv0--trellis-api-fastapi-app.modal.run"
            )

        return {
            "job_id": job_id,
            "status": "completed",
            "output_filename": output_filename,
            "output_size_bytes": len(output_bytes),
        }

    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()[:500]}"
        print(f"[Job {job_id}] Error: {error_msg}")
        job_data = job_store.update_job(
            job_id,
            status=JobStatus.FAILED.value,
            error=error_msg,
            message="Processing failed",
        )

        # Send callback on failure too
        if callback_url:
            send_callback(
                callback_url,
                job_data,
                base_url="https://nayardhruv0--trellis-api-fastapi-app.modal.run"
            )

        raise


# ============================================================================
# FastAPI Application
# ============================================================================
@app.function(
    image=rembg_image,
    timeout=600,
    secrets=[api_keys_secret],
    volumes={"/results": results_volume},
)
@modal.asgi_app()
def fastapi_app():
    """Serve the FastAPI application."""
    from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Security
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import Response
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from pydantic import BaseModel
    from typing import Optional
    from pathlib import Path
    import os
    import uuid

    # Load API keys from environment (set via Modal secret)
    API_KEYS = set(os.environ.get("API_KEYS", "").split(","))
    API_KEYS.discard("")  # Remove empty strings

    security = HTTPBearer()

    def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
        """Verify the API key from the Authorization header."""
        if not API_KEYS:
            # No keys configured = open access (for testing)
            return credentials.credentials if credentials else "anonymous"

        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="Missing API key. Use header: Authorization: Bearer <your-key>"
            )

        if credentials.credentials not in API_KEYS:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )

        return credentials.credentials

    # Response models for async endpoints
    class AsyncJobResponse(BaseModel):
        job_id: str
        status: str
        job_type: str
        created_at: str
        message: str
        poll_url: str

    class JobStatusResponse(BaseModel):
        job_id: str
        status: str
        job_type: str
        created_at: str
        updated_at: Optional[str] = None
        completed_at: Optional[str] = None
        progress: int
        message: Optional[str] = None
        error: Optional[str] = None
        download_url: Optional[str] = None
        output_size_bytes: Optional[int] = None

    fastapi = FastAPI(
        title="TRELLIS API (Modal)",
        version="2.3.0-modal-async",
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
            "version": "2.3.0-modal-async",
            "endpoints": {
                "health": "/health",
                "rembg_sync": "/api/v1/rembg/",
                "rembg_async": "/api/v1/rembg/async/",
                "trellis_sync": "/api/v1/trellis/",
                "trellis_async": "/api/v1/trellis/async/",
                "jobs": "/api/v1/jobs/{job_id}",
                "job_result": "/api/v1/jobs/{job_id}/result",
            },
            "auth": "Required. Use header: Authorization: Bearer <your-key>",
            "info": {
                "trellis": "Self-hosted on Modal GPU (A10G, 24GB VRAM)",
                "rembg": "CPU-based background removal",
                "async": "Use /async/ endpoints for non-blocking processing with job polling",
            }
        }

    @fastapi.get("/health")
    def health():
        return {"status": "healthy", "version": "2.3.0-modal-async"}

    @fastapi.post("/api/v1/rembg/")
    async def remove_background(
        files: list[UploadFile] = File(...),
        api_key: str = Depends(verify_api_key),
    ):
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
        api_key: str = Depends(verify_api_key),
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

    # ========================================================================
    # ASYNC ENDPOINTS
    # ========================================================================

    @fastapi.post("/api/v1/trellis/async/", response_model=AsyncJobResponse)
    async def trellis_async(
        files: list[UploadFile] = File(...),
        seed: int = 0,
        callback_url: Optional[str] = None,
        api_key: str = Depends(verify_api_key),
    ):
        """Submit async TRELLIS job. Returns immediately with job_id for polling.

        Optionally provide callback_url to receive a POST notification when job completes.
        """
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        file = files[0]
        image_bytes = await file.read()
        job_id = str(uuid.uuid4())

        try:
            # Spawn the GPU function asynchronously
            call = trellis_gpu_inference_async.spawn(
                job_id=job_id,
                image_bytes=image_bytes,
                seed=seed,
                texture_size=1024,
                callback_url=callback_url,
            )

            # Create job record
            job_store = ModalJobStore(job_dict)
            job_data = job_store.create_job(
                job_id=job_id,
                job_type=JobType.TRELLIS,
                modal_call_id=call.object_id,
                input_filename=file.filename or "image.png",
                seed=seed,
                texture_size=1024,
                callback_url=callback_url,
            )

            return AsyncJobResponse(
                job_id=job_id,
                status="pending",
                job_type="trellis",
                created_at=job_data["created_at"],
                message="Job submitted for processing" + (" (callback configured)" if callback_url else ""),
                poll_url=f"/api/v1/jobs/{job_id}",
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to submit job: {e}")

    @fastapi.post("/api/v1/rembg/async/", response_model=AsyncJobResponse)
    async def rembg_async(
        files: list[UploadFile] = File(...),
        model: str = "u2net",
        alpha_matting: bool = False,
        callback_url: Optional[str] = None,
        api_key: str = Depends(verify_api_key),
    ):
        """Submit async RemBG job. Returns immediately with job_id for polling.

        Optionally provide callback_url to receive a POST notification when job completes.
        """
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        file = files[0]
        image_bytes = await file.read()
        job_id = str(uuid.uuid4())

        try:
            call = rembg_process_async.spawn(
                job_id=job_id,
                image_bytes=image_bytes,
                model=model,
                alpha_matting=alpha_matting,
                callback_url=callback_url,
            )

            job_store = ModalJobStore(job_dict)
            job_data = job_store.create_job(
                job_id=job_id,
                job_type=JobType.REMBG,
                modal_call_id=call.object_id,
                input_filename=file.filename or "image.png",
                model=model,
                alpha_matting=alpha_matting,
                callback_url=callback_url,
            )

            return AsyncJobResponse(
                job_id=job_id,
                status="pending",
                job_type="rembg",
                created_at=job_data["created_at"],
                message="Job submitted for processing" + (" (callback configured)" if callback_url else ""),
                poll_url=f"/api/v1/jobs/{job_id}",
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to submit job: {e}")

    @fastapi.get("/api/v1/jobs/{job_id}", response_model=JobStatusResponse)
    async def get_job_status(
        job_id: str,
        api_key: str = Depends(verify_api_key),
    ):
        """Get job status. Poll this endpoint until completed or failed."""
        job_store = ModalJobStore(job_dict)
        job_data = job_store.get_job(job_id)

        if not job_data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Build download URL if completed
        download_url = None
        if job_data["status"] == "completed" and job_data.get("output_filename"):
            download_url = f"/api/v1/jobs/{job_id}/result"

        return JobStatusResponse(
            job_id=job_data["job_id"],
            status=job_data["status"],
            job_type=job_data["job_type"],
            created_at=job_data["created_at"],
            updated_at=job_data.get("updated_at"),
            completed_at=job_data.get("completed_at"),
            progress=job_data.get("progress", 0),
            message=job_data.get("message"),
            error=job_data.get("error"),
            download_url=download_url,
            output_size_bytes=job_data.get("output_size_bytes"),
        )

    @fastapi.get("/api/v1/jobs/{job_id}/result")
    async def download_result(
        job_id: str,
        api_key: str = Depends(verify_api_key),
    ):
        """Download result file from completed job."""
        job_store = ModalJobStore(job_dict)
        job_data = job_store.get_job(job_id)

        if not job_data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        if job_data["status"] != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Job is not completed (status: {job_data['status']})"
            )

        output_filename = job_data.get("output_filename")
        if not output_filename:
            raise HTTPException(status_code=404, detail="No output file available")

        # Reload volume to see files committed by other containers
        results_volume.reload()

        file_path = Path(f"/results/{output_filename}")
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Result file not found")

        # Determine content type
        suffix = file_path.suffix.lower()
        media_types = {
            ".glb": "model/gltf-binary",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }
        media_type = media_types.get(suffix, "application/octet-stream")

        with open(file_path, "rb") as f:
            content = f.read()

        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{output_filename}"'
            }
        )

    @fastapi.delete("/api/v1/jobs/{job_id}")
    async def cancel_job(
        job_id: str,
        api_key: str = Depends(verify_api_key),
    ):
        """Cancel and delete a job."""
        job_store = ModalJobStore(job_dict)
        job_data = job_store.get_job(job_id)

        if not job_data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Try to cancel the Modal function call
        if job_data.get("modal_call_id") and job_data["status"] in ("pending", "processing"):
            try:
                from modal.functions import FunctionCall
                fc = FunctionCall.from_id(job_data["modal_call_id"])
                fc.cancel()
            except Exception:
                pass  # Best effort cancellation

        # Update status
        job_store.update_job(job_id, status="cancelled", message="Job cancelled by user")

        # Clean up result file if exists
        output_filename = job_data.get("output_filename")
        if output_filename:
            try:
                file_path = Path(f"/results/{output_filename}")
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass

        job_store.delete_job(job_id)

        return {"message": f"Job {job_id} cancelled and deleted"}

    return fastapi


# For local testing with `modal serve`
if __name__ == "__main__":
    print("Run with: modal serve modal_app.py")
    print("Or deploy with: modal deploy modal_app.py")
