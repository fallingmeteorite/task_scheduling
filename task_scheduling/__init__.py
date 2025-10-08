# -*- coding: utf-8 -*-
# Author: fallingmeteorite
from .common import configure_logger

# Initialize logger configuration at module load
configure_logger()

from .config import ensure_config_loaded, config

# Initialize the config dict
ensure_config_loaded()
