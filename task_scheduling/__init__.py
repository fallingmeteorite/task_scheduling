# -*- coding: utf-8 -*-
from .common import configure_logger

# Initialize logger configuration at module load
configure_logger()

from .config import *

# Initialize the config dict
ensure_config_loaded()

__version__ = "2.0.0"
