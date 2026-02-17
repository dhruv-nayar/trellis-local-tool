"""Main pipeline for image to GLB conversion."""

import logging
from pathlib import Path
from typing import Optional, Union

from PIL import Image
import numpy as np

from .model import TRELLISModelManager
from .exporter import GLBExporter


logger = logging.getLogger(__name__)


class TRELLISPipeline:
    """Main pipeline for converting images to GLB files."""

    def __init__(
        self,
        model_name: str = "microsoft/TRELLIS-image-large",
        device: str = "auto",
        cache_dir: Optional[str] = None,
        seed: Optional[int] = 1,
        texture_size: int = 2048,
        optimize: bool = True,
        target_faces: Optional[int] = None,
    ):
        """
        Initialize the TRELLIS pipeline.

        Args:
            model_name: TRELLIS model to use
            device: Computation device ("cuda", "cpu", or "auto")
            cache_dir: Cache directory for models
            seed: Random seed for reproducibility
            texture_size: Output texture resolution
            optimize: Whether to optimize meshes
            target_faces: Target face count for optimization
        """
        self.model_manager = TRELLISModelManager(model_name, device, cache_dir)
        self.exporter = GLBExporter(texture_size, optimize, target_faces)
        self.seed = seed
        self._pipeline = None

    def setup(self):
        """Load the TRELLIS model."""
        logger.info("Setting up TRELLIS pipeline...")
        self._pipeline = self.model_manager.load_pipeline()
        logger.info("✓ Pipeline ready")

    def process_image(
        self,
        image_path: Union[str, Path],
        output_path: Union[str, Path],
        seed: Optional[int] = None,
    ) -> Path:
        """
        Convert an image to a GLB file.

        Args:
            image_path: Path to input image
            output_path: Path for output GLB file
            seed: Random seed (overrides default)

        Returns:
            Path to the generated GLB file
        """
        image_path = Path(image_path)
        output_path = Path(output_path)

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        logger.info(f"Processing: {image_path.name}")

        # Load pipeline if not already loaded
        if self._pipeline is None:
            self.setup()

        # Load and preprocess image
        image = self._load_image(image_path)

        # Run TRELLIS pipeline
        logger.info("Running TRELLIS inference...")
        outputs = self._run_inference(image, seed or self.seed)

        # Export to GLB
        output_path = self.exporter.export(outputs, output_path)

        # Log memory usage
        if self.model_manager.device == "cuda":
            memory_stats = self.model_manager.get_memory_usage()
            logger.debug(f"GPU Memory: {memory_stats.get('allocated', 0):.2f} GB used")

        return output_path

    def _load_image(self, image_path: Path) -> Image.Image:
        """
        Load and preprocess an image.

        Args:
            image_path: Path to image file

        Returns:
            PIL Image object
        """
        try:
            image = Image.open(image_path)

            # Convert to RGB if needed
            if image.mode != "RGB":
                logger.debug(f"Converting image from {image.mode} to RGB")
                image = image.convert("RGB")

            logger.debug(f"Loaded image: {image.size[0]}x{image.size[1]}")

            return image

        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            raise

    def _run_inference(self, image: Image.Image, seed: int) -> dict:
        """
        Run TRELLIS inference on an image.

        Args:
            image: PIL Image object
            seed: Random seed

        Returns:
            Dictionary with TRELLIS outputs
        """
        try:
            # Set seed for reproducibility
            if seed is not None:
                import torch
                import random
                torch.manual_seed(seed)
                np.random.seed(seed)
                random.seed(seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(seed)

            # Run pipeline
            outputs = self._pipeline.run(image, seed=seed)

            logger.info("✓ Inference complete")

            return outputs

        except Exception as e:
            logger.error(f"Inference failed: {e}")
            raise

    def process_batch(
        self,
        image_paths: list[Path],
        output_dir: Path,
        naming_pattern: str = "{name}",
    ) -> list[Path]:
        """
        Process multiple images in batch.

        Args:
            image_paths: List of image paths to process
            output_dir: Output directory for GLB files
            naming_pattern: Naming pattern for output files

        Returns:
            List of paths to generated GLB files
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Load pipeline once
        if self._pipeline is None:
            self.setup()

        results = []
        failed = []

        for i, image_path in enumerate(image_paths, 1):
            logger.info(f"\n[{i}/{len(image_paths)}] Processing: {image_path.name}")

            try:
                # Generate output filename
                output_name = self._generate_output_name(image_path, naming_pattern, i)
                output_path = output_dir / output_name

                # Process image
                result_path = self.process_image(image_path, output_path)
                results.append(result_path)

            except Exception as e:
                logger.error(f"Failed to process {image_path.name}: {e}")
                failed.append(image_path)
                continue

        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"Batch complete: {len(results)}/{len(image_paths)} successful")
        if failed:
            logger.warning(f"Failed: {len(failed)} images")
            for path in failed:
                logger.warning(f"  - {path.name}")
        logger.info(f"{'='*60}")

        return results

    def _generate_output_name(self, image_path: Path, pattern: str, index: int) -> str:
        """
        Generate output filename based on pattern.

        Args:
            image_path: Input image path
            pattern: Naming pattern
            index: Image index in batch

        Returns:
            Output filename
        """
        import time

        name_without_ext = image_path.stem
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        output_name = pattern.format(
            name=name_without_ext,
            timestamp=timestamp,
            index=index,
            seed=self.seed,
        )

        # Ensure .glb extension
        if not output_name.endswith(".glb"):
            output_name += ".glb"

        return output_name

    def cleanup(self):
        """Clean up resources."""
        self.model_manager.unload_pipeline()
        self._pipeline = None
        logger.info("Pipeline cleaned up")
