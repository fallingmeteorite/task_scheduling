# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from .log_config import configure_logger, logger, set_log_level
    from .config import config, ensure_config_loaded, update_config
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['configure_logger', 'logger', 'set_log_level', 'config', 'ensure_config_loaded', 'update_config']
