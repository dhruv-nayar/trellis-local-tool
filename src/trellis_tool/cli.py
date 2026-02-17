"""Command-line interface for TRELLIS local tool."""

import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from .core.pipeline import TRELLISPipeline
from .utils.config import Config
from .utils.logging_setup import setup_logging, ProgressLogger
from .utils.image import find_images, get_image_info


console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    help="Logging level",
)
@click.pass_context
def main(ctx, config: Optional[Path], log_level: str):
    """TRELLIS Local Tool - Convert images to 3D GLB files."""
    # Load configuration
    if config:
        ctx.obj = Config(config)
    else:
        # Look for config in current directory
        default_config = Path("config.yaml")
        ctx.obj = Config(default_config if default_config.exists() else None)

    # Setup logging
    log_file = ctx.obj.get("logging.log_file")
    setup_logging(
        level=log_level,
        log_file=Path(log_file) if log_file else None,
        rich_output=True,
    )


@main.command()
@click.argument("image", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output GLB file path",
)
@click.option(
    "--model",
    "-m",
    type=str,
    help="Model name (default: microsoft/TRELLIS-image-large)",
)
@click.option(
    "--device",
    "-d",
    type=click.Choice(["auto", "cuda", "cpu"]),
    help="Device to use (default: auto)",
)
@click.option(
    "--seed",
    "-s",
    type=int,
    help="Random seed for reproducibility",
)
@click.option(
    "--texture-size",
    type=click.Choice(["512", "1024", "2048", "4096"]),
    help="Texture resolution",
)
@click.option(
    "--optimize/--no-optimize",
    default=None,
    help="Optimize mesh geometry",
)
@click.option(
    "--target-faces",
    type=int,
    help="Target face count for optimization",
)
@click.pass_obj
def convert(
    config: Config,
    image: Path,
    output: Optional[Path],
    model: Optional[str],
    device: Optional[str],
    seed: Optional[int],
    texture_size: Optional[str],
    optimize: Optional[bool],
    target_faces: Optional[int],
):
    """Convert a single image to GLB format."""
    try:
        # Validate image
        if not image.exists():
            console.print(f"[red]Error: Image not found: {image}[/red]")
            sys.exit(1)

        # Set output path
        if not output:
            output_dir = Path(config.get("output.output_dir", "./output"))
            output_dir.mkdir(parents=True, exist_ok=True)
            output = output_dir / f"{image.stem}.glb"

        # Build pipeline configuration
        pipeline_config = {
            "model_name": model or config.get("model.name"),
            "device": device or config.get("model.device"),
            "cache_dir": config.get("model.cache_dir"),
            "seed": seed or config.get("processing.seed"),
            "texture_size": int(texture_size) if texture_size else config.get("output.texture_size"),
            "optimize": optimize if optimize is not None else config.get("output.optimize"),
            "target_faces": target_faces or config.get("output.target_faces"),
        }

        # Display configuration
        console.print("\n[bold cyan]TRELLIS Image to GLB Converter[/bold cyan]")
        console.print(f"[dim]Model: {pipeline_config['model_name']}[/dim]")
        console.print(f"[dim]Device: {pipeline_config['device']}[/dim]")
        console.print()

        # Create pipeline
        pipeline = TRELLISPipeline(**pipeline_config)

        # Process image
        result = pipeline.process_image(image, output, seed=pipeline_config["seed"])

        # Success message
        console.print(f"\n[bold green]✓ Success![/bold green]")
        console.print(f"Output: [cyan]{result}[/cyan]")
        console.print(f"Size: {result.stat().st_size / 1e6:.2f} MB\n")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        logger.exception("Conversion failed")
        sys.exit(1)


@main.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory for GLB files",
)
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    help="Search for images recursively",
)
@click.option(
    "--pattern",
    "-p",
    type=str,
    default="{name}",
    help="Output naming pattern (supports: {name}, {timestamp}, {index}, {seed})",
)
@click.option(
    "--model",
    "-m",
    type=str,
    help="Model name",
)
@click.option(
    "--device",
    "-d",
    type=click.Choice(["auto", "cuda", "cpu"]),
    help="Device to use",
)
@click.option(
    "--seed",
    "-s",
    type=int,
    help="Random seed",
)
@click.pass_obj
def batch(
    config: Config,
    input_path: Path,
    output_dir: Optional[Path],
    recursive: bool,
    pattern: str,
    model: Optional[str],
    device: Optional[str],
    seed: Optional[int],
):
    """Process multiple images in batch mode."""
    try:
        # Find images
        console.print("\n[bold cyan]TRELLIS Batch Converter[/bold cyan]")
        console.print(f"Scanning: [cyan]{input_path}[/cyan]")

        images = find_images(input_path, recursive=recursive)

        if not images:
            console.print("[yellow]No images found[/yellow]")
            sys.exit(0)

        console.print(f"Found: [green]{len(images)}[/green] images\n")

        # Set output directory
        if not output_dir:
            output_dir = Path(config.get("output.output_dir", "./output"))

        # Build pipeline configuration
        pipeline_config = {
            "model_name": model or config.get("model.name"),
            "device": device or config.get("model.device"),
            "cache_dir": config.get("model.cache_dir"),
            "seed": seed or config.get("processing.seed"),
            "texture_size": config.get("output.texture_size"),
            "optimize": config.get("output.optimize"),
            "target_faces": config.get("output.target_faces"),
        }

        # Create pipeline
        console.print(f"[dim]Model: {pipeline_config['model_name']}[/dim]")
        console.print(f"[dim]Device: {pipeline_config['device']}[/dim]")
        console.print()

        pipeline = TRELLISPipeline(**pipeline_config)

        # Process batch
        results = pipeline.process_batch(images, output_dir, naming_pattern=pattern)

        # Summary
        console.print(f"\n[bold green]✓ Batch complete![/bold green]")
        console.print(f"Processed: [cyan]{len(results)}/{len(images)}[/cyan] images")
        console.print(f"Output directory: [cyan]{output_dir}[/cyan]\n")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        logger.exception("Batch processing failed")
        sys.exit(1)


@main.command()
@click.argument("image", type=click.Path(exists=True, path_type=Path))
def info(image: Path):
    """Display information about an image."""
    try:
        info_data = get_image_info(image)

        if not info_data:
            console.print("[red]Failed to read image[/red]")
            sys.exit(1)

        console.print(f"\n[bold]Image Information:[/bold]")
        console.print(f"  Path: [cyan]{info_data['path']}[/cyan]")
        console.print(f"  Format: {info_data['format']}")
        console.print(f"  Mode: {info_data['mode']}")
        console.print(f"  Size: {info_data['width']} x {info_data['height']} pixels")
        console.print(f"  File Size: {info_data['file_size'] / 1e6:.2f} MB\n")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option(
    "--model",
    "-m",
    type=click.Choice(
        [
            "microsoft/TRELLIS-image-large",
            "microsoft/TRELLIS-text-large",
            "microsoft/TRELLIS-text-xlarge",
        ]
    ),
    default="microsoft/TRELLIS-image-large",
    help="Model to download",
)
def setup(model: str):
    """Download and setup TRELLIS model."""
    try:
        console.print("\n[bold cyan]TRELLIS Setup[/bold cyan]")
        console.print(f"Model: [cyan]{model}[/cyan]\n")

        console.print("[yellow]This will download the TRELLIS model (~5GB).[/yellow]")
        console.print("Make sure you have:")
        console.print("  • NVIDIA GPU with ≥16GB VRAM")
        console.print("  • CUDA 11.8 or 12.2 installed")
        console.print("  • ~10GB disk space\n")

        if not click.confirm("Continue?"):
            console.print("Setup cancelled")
            sys.exit(0)

        # Create pipeline (this will trigger model download)
        from .core.model import TRELLISModelManager

        console.print("\nDownloading model...")
        manager = TRELLISModelManager(model_name=model)
        manager.load_pipeline()

        console.print("\n[bold green]✓ Setup complete![/bold green]")
        console.print("You can now use: [cyan]trellis-tool convert image.jpg[/cyan]\n")

    except Exception as e:
        console.print(f"\n[bold red]Setup failed: {e}[/bold red]")
        logger.exception("Setup failed")
        sys.exit(1)


@main.command()
@click.pass_obj
def config_show(config: Config):
    """Display current configuration."""
    import yaml

    console.print("\n[bold]Current Configuration:[/bold]\n")
    console.print(yaml.dump(config.data, default_flow_style=False, sort_keys=False))


if __name__ == "__main__":
    main()
