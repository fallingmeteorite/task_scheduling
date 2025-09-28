# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import os
from functools import lru_cache
from typing import Dict, Any

import yaml

from ..common import logger

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
        _file_path (str): Path to the configuration file. If not provided, defaults to 'config.yaml' in the package directory.

    Returns:
        bool: Whether the configuration file was successfully loaded.
    """
    if _file_path is None:
        _file_path = f'{_get_package_directory()}/config.yaml'

    try:
        with open(_file_path, 'r', encoding='utf-8') as f:
            # Safely load the YAML file using yaml.safe_load
            global config
            config.update(yaml.safe_load(f) or {})
            return True  # Return True indicating successful loading
    except Exception as error:
        return error  # Return False indicating loading failure


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
        return error  # Return False indicating update failure


def _save_config(_file_path: str = None) -> bool:
    """
    Save the current in-memory configuration to the configuration file.

    Args:
        _file_path (str): Path to the configuration file. If not provided, defaults to 'config.yaml' in the package directory.

    Returns:
        bool: Whether the configuration was successfully saved to the file.
    """
    if _file_path is None:
        _file_path = f'{_get_package_directory()}/config.yaml'

    try:
        with open(_file_path, 'w', encoding='utf-8') as f:
            global config
            yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True)
        logger.info("Configuration saved to file successfully")
        return True
    except Exception as error:
        logger.error(f"Unknown error occurred while saving configuration to file: {error}")
    return False


def ensure_config_loaded():
    """
    Ensure that the configuration file is loaded into the global variable `config`.
    If the configuration is not loaded, attempt to load it and log a warning if loading fails.
    """
    global config
    if not config and not _load_config():
        logger.warning("Configuration file loading failed, the program may not run normally")
