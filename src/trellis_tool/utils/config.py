"""Configuration management."""

import logging
from pathlib import Path
from typing import Any, Optional

import yaml


logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for TRELLIS tool."""

    DEFAULT_CONFIG = {
        "model": {
            "name": "microsoft/TRELLIS-image-large",
            "device": "auto",
            "cache_dir": "~/.cache/trellis",
        },
        "processing": {
            "seed": 1,
            "steps": 50,
            "sparsity": 0.5,
        },
        "output": {
            "format": "glb",
            "texture_size": 2048,
            "optimize": True,
            "target_faces": None,
            "output_dir": "./output",
            "naming_pattern": "{name}",
        },
        "logging": {
            "level": "INFO",
            "log_file": None,
            "show_progress": True,
        },
    }

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to YAML config file
        """
        self.config_path = config_path
        self.data = self.DEFAULT_CONFIG.copy()

        if config_path and config_path.exists():
            self.load(config_path)

    def load(self, config_path: Path):
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config file
        """
        try:
            with open(config_path, "r") as f:
                user_config = yaml.safe_load(f)

            # Deep merge with defaults
            self.data = self._deep_merge(self.DEFAULT_CONFIG, user_config)

            logger.debug(f"Loaded config from: {config_path}")

        except Exception as e:
            logger.warning(f"Failed to load config: {e}, using defaults")

    def save(self, config_path: Path):
        """
        Save configuration to YAML file.

        Args:
            config_path: Path to save config
        """
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, "w") as f:
                yaml.dump(self.data, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Config saved to: {config_path}")

        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            key: Configuration key (e.g., "model.name")
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self.data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        Set a configuration value using dot notation.

        Args:
            key: Configuration key (e.g., "model.name")
            value: Value to set
        """
        keys = key.split(".")
        target = self.data

        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]

        target[keys[-1]] = value

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """
        Deep merge two dictionaries.

        Args:
            base: Base dictionary
            override: Dictionary to merge in

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Config._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def __repr__(self) -> str:
        """String representation."""
        return f"Config({self.config_path})"
