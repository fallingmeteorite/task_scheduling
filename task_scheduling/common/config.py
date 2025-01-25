# -*- coding: utf-8 -*-
from typing import Dict, Any

import yaml

from ..common.log_config import logger

# Global configuration dictionary to store loaded configurations
config: Dict = {}


def get_package_directory() -> str:
    """
    Get the path of the directory containing the __init__.py file.

    Returns:
        str: Path of the package directory.
    """
    import os
    return os.path.dirname(__file__)


def load_config(file_path=f'{get_package_directory()}/config.yaml') -> bool:
    """
    Load the configuration file into the global variable `config`.

    Args:
        file_path (str): Path to the configuration file.

    Returns:
        bool: Whether the configuration file was successfully loaded.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Safely load the YAML file using yaml.safe_load
            config.update(yaml.safe_load(f))
            logger.info("Configuration file loaded successfully")
            return True  # Return True indicating successful loading
    except Exception as error:
        logger.error(f"Unknown error occurred while loading configuration file: {error}")
    return False  # Return False indicating loading failure


def update_config(key: str, value: Any, file_path=f'{get_package_directory()}/config.yaml') -> bool:
    """
    Update a specific key-value pair in the configuration file, save the changes,
    and reload the configuration to ensure the global `config` is up-to-date.

    Args:
        key (str): The key to update in the configuration file.
        value: The new value to set for the specified key.
        file_path (str): Path to the configuration file.

    Returns:
        bool: Whether the configuration file was successfully updated and reloaded.
    """
    try:
        # Load the current configuration
        with open(file_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f) or {}

        # Update the specified key with the new value
        config_data[key] = value

        # Write the updated configuration back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config_data, f, default_flow_style=False, allow_unicode=True)

        # Reload the configuration to update the global `config` variable
        if not load_config(file_path):
            logger.error("Failed to reload configuration after update")
            return False

        logger.info(f"Configuration file updated and reloaded successfully: {key} = {value}")
        return True  # Return True indicating successful update and reload
    except Exception as error:
        logger.error(f"Unknown error occurred while updating configuration file: {error}")
    return False  # Return False indicating update failure



# Load configuration file
if not load_config(f'{get_package_directory()}/config.yaml'):
    logger.warning("Configuration file loading failed, the program may not run normally")
