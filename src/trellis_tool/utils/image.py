"""Image processing and validation utilities."""

import logging
from pathlib import Path
from typing import List

from PIL import Image


logger = logging.getLogger(__name__)


SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def validate_image(image_path: Path) -> bool:
    """
    Validate an image file.

    Args:
        image_path: Path to image file

    Returns:
        True if valid, False otherwise
    """
    if not image_path.exists():
        logger.error(f"Image not found: {image_path}")
        return False

    if not image_path.is_file():
        logger.error(f"Not a file: {image_path}")
        return False

    if image_path.suffix.lower() not in SUPPORTED_FORMATS:
        logger.error(f"Unsupported format: {image_path.suffix}")
        return False

    try:
        with Image.open(image_path) as img:
            img.verify()
        return True
    except Exception as e:
        logger.error(f"Invalid image {image_path}: {e}")
        return False


def find_images(path: Path, recursive: bool = False) -> List[Path]:
    """
    Find all images in a directory or return single image.

    Args:
        path: Path to file or directory
        recursive: Search recursively in subdirectories

    Returns:
        List of image paths
    """
    if path.is_file():
        if validate_image(path):
            return [path]
        else:
            return []

    if path.is_dir():
        images = []

        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"

        for ext in SUPPORTED_FORMATS:
            images.extend(path.glob(f"{pattern}{ext}"))
            images.extend(path.glob(f"{pattern}{ext.upper()}"))

        # Filter valid images
        valid_images = [img for img in images if validate_image(img)]

        logger.info(f"Found {len(valid_images)} images in {path}")

        return sorted(valid_images)

    logger.error(f"Path not found: {path}")
    return []


def get_image_info(image_path: Path) -> dict:
    """
    Get information about an image.

    Args:
        image_path: Path to image

    Returns:
        Dictionary with image information
    """
    try:
        with Image.open(image_path) as img:
            return {
                "path": image_path,
                "format": img.format,
                "mode": img.mode,
                "size": img.size,
                "width": img.width,
                "height": img.height,
                "file_size": image_path.stat().st_size,
            }
    except Exception as e:
        logger.error(f"Failed to get image info: {e}")
        return {}


def preprocess_image(image_path: Path, max_size: int = 1024) -> Image.Image:
    """
    Preprocess an image for TRELLIS.

    Args:
        image_path: Path to image
        max_size: Maximum dimension size

    Returns:
        Preprocessed PIL Image
    """
    img = Image.open(image_path)

    # Convert to RGB
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Resize if too large
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = tuple(int(dim * ratio) for dim in img.size)
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        logger.debug(f"Resized image to {new_size}")

    return img
