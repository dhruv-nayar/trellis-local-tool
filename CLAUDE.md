# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TRELLIS Local Tool is a CLI application that converts images to 3D GLB files using Microsoft's TRELLIS model (1.2B parameters). It provides both a command-line interface and a REST API server.

## Common Commands

### Development Setup
```bash
./scripts/setup_trellis.sh    # Install TRELLIS dependencies
pip install -e .               # Install package in editable mode
pip install -e ".[dev]"        # Install with dev dependencies
trellis-tool setup             # Download TRELLIS model (~5GB)
```

### CLI Usage
```bash
trellis-tool convert image.jpg                    # Single image conversion
trellis-tool convert image.jpg -o output.glb      # Specify output path
trellis-tool batch ./images/ -r                   # Batch with recursive search
trellis-tool info image.jpg                       # Display image metadata
trellis-tool config-show                          # Show current config
trellis-tool --config custom.yaml convert img.jpg # Use custom config
```

### Code Quality
```bash
black src/                     # Format code
ruff check src/                # Lint code
pytest tests/                  # Run tests
```

### API Server (v2 with Celery)
```bash
cd api && docker-compose up --build   # Full stack: Redis + API + Celery workers
cd api && uvicorn api.main:app --reload  # API only (requires external Redis)
```

### API Testing
```bash
# Test RemBG endpoint
curl -X POST -H "Authorization: Bearer dev-key-12345" \
  -F "files=@test.jpg" http://localhost:8000/api/v1/rembg

# Test TRELLIS endpoint
curl -X POST -H "Authorization: Bearer dev-key-12345" \
  -F "files=@image.jpg" http://localhost:8000/api/v1/trellis

# Check job status
curl -H "Authorization: Bearer dev-key-12345" \
  http://localhost:8000/api/v1/jobs/{job_id}
```

## Architecture

### CLI Tool
```
src/trellis_tool/
├── cli.py                 # Click-based CLI entry point (6 commands)
├── core/
│   ├── pipeline.py        # TRELLISPipeline - orchestrates conversion workflow
│   ├── model.py           # TRELLISModelManager - model loading/GPU management
│   └── exporter.py        # GLBExporter - mesh export with trimesh
└── utils/
    ├── config.py          # YAML config with dot-notation access
    ├── logging_setup.py   # Rich-formatted logging and progress bars
    └── image.py           # Image validation and preprocessing
```

### API Server (v2)
```
api/
├── main.py                 # FastAPI app with routers
├── config.py               # Pydantic Settings (env vars)
├── routers/
│   ├── rembg.py            # POST /api/v1/rembg
│   ├── trellis.py          # POST /api/v1/trellis
│   ├── jobs.py             # GET/DELETE /api/v1/jobs/{job_id}
│   └── health.py           # GET /health
├── services/
│   ├── rembg_service.py    # Background removal with rembg
│   ├── trellis_v1.py       # HuggingFace Gradio client
│   ├── trellis_v2.py       # RunPod self-hosted client
│   ├── job_store.py        # Redis job state management
│   └── storage.py          # File upload/download
├── tasks/
│   ├── celery_app.py       # Celery config (Redis broker)
│   ├── rembg_tasks.py      # RemBG Celery task
│   └── trellis_tasks.py    # TRELLIS Celery task
└── middleware/
    ├── auth.py             # API key validation
    └── rate_limit.py       # slowapi rate limiting
```

### Key Classes

- **TRELLISPipeline** (`core/pipeline.py`): Main orchestrator. Call `setup()` to load model, `process_image()` for single conversion, `process_batch()` for multiple images, `cleanup()` to free memory.

- **TRELLISModelManager** (`core/model.py`): Handles TRELLIS model lifecycle. Auto-detects GPU, manages CUDA memory, loads model from HuggingFace Hub.

- **GLBExporter** (`core/exporter.py`): Converts TRELLIS output to GLB using trimesh. Supports mesh optimization via quadric decimation.

- **Config** (`utils/config.py`): Loads `config.yaml` with defaults. Access values via dot-notation: `config.get("model.device")`.

### Data Flow (CLI)

1. CLI parses args → loads Config
2. TRELLISPipeline initializes with TRELLISModelManager
3. Image validated/preprocessed via `utils/image.py`
4. TRELLIS inference runs on GPU
5. GLBExporter creates optimized mesh
6. Output saved to configured directory

### Data Flow (API)

1. Client POSTs images to `/api/v1/rembg` or `/api/v1/trellis`
2. Files saved to `uploads/{job_id}/`, job created in Redis
3. Celery task queued (rembg or trellis queue)
4. Worker processes task, updates job status in Redis
5. Client polls `/api/v1/jobs/{job_id}` for status
6. On completion, download from `download_urls`

### External Dependencies

TRELLIS is expected at `~/.cache/trellis/repo` (installed via `setup_trellis.sh`). The pipeline imports from `trellis.pipelines.TrellisImageTo3DPipeline`.

## Configuration

### CLI Config
Default config in `config.yaml`. Key settings:
- `model.device`: "auto", "cuda", or "cpu"
- `output.texture_size`: 512, 1024, 2048, or 4096
- `output.optimize`: Enable mesh simplification
- `processing.seed`: For reproducible outputs

CLI options override config file values.

### API Config
Environment variables (see `api/.env.example`):
- `API_KEYS`: Comma-separated valid API keys
- `REDIS_URL`: Redis connection URL
- `TRELLIS_BACKEND`: "huggingface" (V1) or "runpod" (V2)
- `RUNPOD_ENDPOINT`, `RUNPOD_API_KEY`: For V2 self-hosted

## Hardware Requirements

- GPU: ≥16GB VRAM (A100, A6000, RTX 4090)
- RAM: ≥32GB
- CUDA: 11.8 or 12.2

## Code Style

- Black formatting, 100 char line length
- Ruff linting, Python 3.8+ target
- Type hints on all public interfaces
- Logging via module-level `logger = logging.getLogger(__name__)`
