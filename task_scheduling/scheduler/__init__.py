# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys
import sysconfig

# Prevent errors during multi-process initialization
try:
    from .api import add_api, kill_api, pause_api, resume_api, get_result_api, shutdown_api, \
        cleanup_results_api

    if sysconfig.get_config_var("Py_GIL_DISABLED") == 1:
        from ..common import logger

        logger.warning("Currently running in no GIL mode!")

except KeyboardInterrupt:
    sys.exit(0)
__all__ = ['add_api', 'kill_api', 'pause_api', 'resume_api', 'get_result_api', 'shutdown_api',
           'cleanup_results_api']
