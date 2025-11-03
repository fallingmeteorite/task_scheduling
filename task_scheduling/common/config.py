# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import os
import json

from functools import lru_cache
from typing import Dict, Any

# Global configuration dictionary to store loaded configurations
config: Dict = {}


@lru_cache(maxsize=1)
def _get_package_directory() -> str:
    """
    Get the path of the directory containing the __init__.py file.

    Returns:
        str: Path of the package directory.
    """
    return os.path.dirname(os.path.abspath(__file__))


def _load_config(_file_path: str = None) -> Any:
    """
    Load the configuration file into the global variable `config`.

    Args:
        _file_path (str): Path to the configuration file. If not provided, defaults to 'config.json' in the package directory.

    Returns:
        bool: Whether the configuration file was successfully loaded.
    """
    if _file_path is None:
        _file_path = f'{_get_package_directory()}\\config.json'

    try:
        with open(_file_path, 'r', encoding='utf-8') as f:
            # Load the JSON file
            global config
            loaded_config = json.load(f)
            config.update(loaded_config or {})
            return True  # Return True indicating successful loading
    except Exception as error:
        return error  # Return the error indicating loading failure


def update_config(key: str,
                  value: Any) -> Any:
    """
    Update a specific key-value pair in the global configuration dictionary.
    Changes are only applied in memory and do not persist to the file.

    Args:
        key (str): The key to update in the configuration dictionary.
        value: The new value to set for the specified key.

    Returns:
        bool: Whether the configuration was successfully updated in memory.
    """
    try:
        # Update the global config directly
        global config
        config[key] = value
        return True  # Return True indicating successful update
    except Exception as error:
        return error  # Return the error indicating update failure


def ensure_config_loaded():
    """
    Ensure that the configuration file is loaded into the global variable `config`.
    If the configuration is not loaded, attempt to load it and log a warning if loading fails.
    """
    global config
    if not config:
        result = _load_config()
        if result is not True:
            raise FileNotFoundError("Configuration file loading failed")
