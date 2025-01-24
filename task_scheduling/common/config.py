# -*- coding: utf-8 -*-
from typing import Dict

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


# Load configuration file
if not load_config(f'{get_package_directory()}/config.yaml'):
    logger.warning("Configuration file loading failed, the program may not run normally")
