# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from .end_cleaning import exit_cleanup
    from .info_share import SharedStatusInfo
    from .priority_check import TaskCounter
    from .parameter_check import get_param_count, retry_on_error_decorator_check
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['exit_cleanup', 'SharedStatusInfo', 'TaskCounter', 'get_param_count', 'retry_on_error_decorator_check']
