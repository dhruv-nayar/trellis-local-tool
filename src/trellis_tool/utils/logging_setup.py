"""Logging setup utilities."""

import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)


def setup_logging(level: str = "INFO", log_file: Optional[Path] = None, rich_output: bool = True):
    """
    Set up logging configuration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file to write logs to
        rich_output: Use rich formatting for console output
    """
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set level
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Console handler with rich formatting
    if rich_output:
        console_handler = RichHandler(
            console=Console(stderr=True),
            show_time=False,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
        )
    else:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        root_logger.addHandler(file_handler)


def create_progress_bar() -> Progress:
    """
    Create a rich progress bar for batch processing.

    Returns:
        Progress bar object
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=Console(stderr=True),
    )


class ProgressLogger:
    """Context manager for progress tracking."""

    def __init__(self, total: int, description: str = "Processing"):
        """
        Initialize progress logger.

        Args:
            total: Total number of items
            description: Description for progress bar
        """
        self.total = total
        self.description = description
        self.progress = None
        self.task = None

    def __enter__(self):
        """Start progress tracking."""
        self.progress = create_progress_bar()
        self.progress.start()
        self.task = self.progress.add_task(self.description, total=self.total)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop progress tracking."""
        if self.progress:
            self.progress.stop()

    def update(self, advance: int = 1, description: Optional[str] = None):
        """
        Update progress.

        Args:
            advance: Number of items completed
            description: Optional updated description
        """
        if self.progress and self.task is not None:
            kwargs = {"advance": advance}
            if description:
                kwargs["description"] = description
            self.progress.update(self.task, **kwargs)
