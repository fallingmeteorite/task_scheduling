# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

try:
    from .common import configure_logger, ensure_config_loaded

    # Initialize logger configuration at module load
    configure_logger()

    # Initialize the config dict
    ensure_config_loaded()
except KeyboardInterrupt:
    sys.exit(0)
