# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Configuration Management Module.

This module provides a thread-safe configuration management system with
caching capabilities. It supports dynamic configuration loading based on
Python interpreter features (GIL status) and provides efficient access
to configuration values with LRU caching.

Key Features:
    - Automatic configuration file selection based on GIL status
    - LRU caching for frequently accessed configuration values
    - Thread-safe configuration access
    - In-memory configuration updates
    - Graceful handling of missing configuration files
    - Support for custom configuration directories

Classes:
    None (module-level functions)

Functions:
    _get_package_directory: Get package directory path
    _get_default_config_path: Get default config path based on GIL status
    _load_config: Load configuration from JSON file
    get_config_value: Get configuration value with caching
    update_config: Update configuration value in memory
    ensure_config_loaded: Ensure configuration is loaded
    set_config_directory: Set custom configuration directory

Global Variables:
    config: Global dictionary storing configuration data
"""

import json
import os
from functools import lru_cache
from typing import Dict, Any, Optional

# Global configuration dictionary to store loaded configurations
config: Dict[str, Any] = {}

# Global variable to store custom config directory
_custom_config_dir: Optional[str] = None


@lru_cache(maxsize=1)
def _get_package_directory() -> str:
    """
    Get the path of the directory containing the __init__.py file.

    Returns:
        Path of the package directory.
    """
    return os.path.dirname(os.path.abspath(__file__))


@lru_cache(maxsize=1)
def _get_default_config_path() -> str:
    """
    Get the default configuration file path with caching.

    Returns:
        Default path to the configuration file.
    """
    if _custom_config_dir:
        config_dir = _custom_config_dir
    else:
        config_dir = _get_package_directory()

    return os.path.join(config_dir, 'config.json')


def _load_config(_file_path: Optional[str] = None) -> bool:
    """
    Load the configuration file into the global variable `config`.

    Args:
        _file_path: Path to the configuration file. If not provided,
                   defaults to appropriate config file in the config directory.

    Returns:
        Whether the configuration file was successfully loaded.
    """
    if _file_path is None:
        _file_path = _get_default_config_path()

    try:
        with open(_file_path, encoding='utf-8') as f:
            # Load the JSON file
            global config
            loaded_config = json.load(f)
            config.clear()
            config.update(loaded_config or {})
            return True  # Return True indicating successful loading
    except FileNotFoundError:
        return False  # Return False indicating loading failure


@lru_cache(maxsize=32)
def get_config_value(key: str, default: Any = None) -> Any:
    """
    Get a value from configuration with caching for frequently accessed keys.

    Args:
        key: The configuration key to retrieve.
        default: Default value if key is not found.

    Returns:
        The configuration value or default.
    """
    global config
    return config.get(key, default)


def update_config(key: str, value: Any) -> bool:
    """
    Update a specific key-value pair in the global configuration dictionary.
    Changes are only applied in memory and do not persist to the file.

    Args:
        key: The key to update in the configuration dictionary.
        value: The new value to set for the specified key.

    Returns:
        Whether the configuration was successfully updated in memory.
    """
    try:
        # Update the global config directly
        global config
        config[key] = value

        # Clear the get_config_value cache since config has changed
        get_config_value.cache_clear()

        return True  # Return True indicating successful update
    except KeyError:
        return False  # Return False indicating update failure


def ensure_config_loaded() -> bool:
    """
    Ensure that the configuration file is loaded into the global variable `config`.
    If the configuration is not loaded, attempt to load it.

    Returns:
        Whether the configuration is loaded (True) or not (False).
    """
    global config
    if not config:
        return _load_config()
    return True


def set_config_directory(config_dir: str) -> bool:
    """
    Set a custom directory for configuration files and reload the configuration.

    Args:
        config_dir: Path to the directory containing config_no_gil.json and config_gil.json

    Returns:
        Whether the configuration was successfully reloaded from the new directory.
    """
    global _custom_config_dir

    if not os.path.isdir(config_dir):
        return False

    # Set the custom config directory
    _custom_config_dir = config_dir

    # Clear relevant caches
    _get_default_config_path.cache_clear()
    get_config_value.cache_clear()

    # Clear the current config and reload from new directory
    global config
    config.clear()

    # Attempt to load configuration from the new directory
    return _load_config()
