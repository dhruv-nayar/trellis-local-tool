"""Model manager for TRELLIS pipeline."""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

import torch


logger = logging.getLogger(__name__)


class TRELLISModelManager:
    """Manages TRELLIS model loading and caching."""

    def __init__(self, model_name: str = "microsoft/TRELLIS-image-large", device: str = "auto", cache_dir: Optional[str] = None):
        """
        Initialize the model manager.

        Args:
            model_name: Name of the TRELLIS model to load
            device: Device to use ("cuda", "cpu", or "auto")
            cache_dir: Directory for model cache
        """
        self.model_name = model_name
        self.cache_dir = Path(cache_dir).expanduser() if cache_dir else Path.home() / ".cache" / "trellis"
        self.device = self._setup_device(device)
        self.pipeline = None
        self._trellis_path = None

    def _setup_device(self, device: str) -> str:
        """
        Set up the computation device.

        Args:
            device: Device preference ("cuda", "cpu", or "auto")

        Returns:
            Device string to use
        """
        if device == "auto":
            if torch.cuda.is_available():
                device = "cuda"
                logger.info(f"Auto-detected CUDA device: {torch.cuda.get_device_name(0)}")
                logger.info(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
            else:
                device = "cpu"
                logger.warning("No CUDA device found, using CPU (this will be slow)")
        elif device == "cuda" and not torch.cuda.is_available():
            logger.error("CUDA requested but not available")
            raise RuntimeError("CUDA is not available. Please use device='cpu' or install CUDA.")

        return device

    def _setup_trellis_path(self):
        """Add TRELLIS to Python path."""
        trellis_repo = self.cache_dir / "repo"

        if not trellis_repo.exists():
            raise RuntimeError(
                f"TRELLIS repository not found at {trellis_repo}. "
                "Please run the setup script: ./scripts/setup_trellis.sh"
            )

        # Add TRELLIS to path
        trellis_path = str(trellis_repo)
        if trellis_path not in sys.path:
            sys.path.insert(0, trellis_path)
            logger.debug(f"Added TRELLIS to path: {trellis_path}")

        self._trellis_path = trellis_repo

    def load_pipeline(self):
        """
        Load the TRELLIS pipeline.

        Returns:
            Loaded pipeline object
        """
        if self.pipeline is not None:
            logger.debug("Pipeline already loaded")
            return self.pipeline

        logger.info(f"Loading TRELLIS model: {self.model_name}")

        # Set up TRELLIS path
        self._setup_trellis_path()

        try:
            # Import TRELLIS modules
            from trellis.pipelines import TrellisImageTo3DPipeline

            # Load pipeline
            self.pipeline = TrellisImageTo3DPipeline.from_pretrained(self.model_name)
            self.pipeline.to(self.device)

            logger.info(f"✓ Model loaded successfully on {self.device}")

            return self.pipeline

        except ImportError as e:
            logger.error(f"Failed to import TRELLIS: {e}")
            raise RuntimeError(
                "TRELLIS not properly installed. Please run: ./scripts/setup_trellis.sh"
            ) from e
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def unload_pipeline(self):
        """Unload the pipeline to free memory."""
        if self.pipeline is not None:
            del self.pipeline
            self.pipeline = None

            if self.device == "cuda":
                torch.cuda.empty_cache()

            logger.info("Pipeline unloaded")

    def get_memory_usage(self) -> dict:
        """
        Get current memory usage.

        Returns:
            Dictionary with memory statistics
        """
        stats = {}

        if self.device == "cuda" and torch.cuda.is_available():
            stats["allocated"] = torch.cuda.memory_allocated() / 1e9
            stats["reserved"] = torch.cuda.memory_reserved() / 1e9
            stats["max_allocated"] = torch.cuda.max_memory_allocated() / 1e9
            stats["total"] = torch.cuda.get_device_properties(0).total_memory / 1e9

        return stats
