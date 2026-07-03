"""Configuration persistence (JSON save/load)."""

from .config_io import config_from_dict, config_to_dict, load_config, save_config

__all__ = ["save_config", "load_config", "config_to_dict", "config_from_dict"]
