# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from .process_control import ProcessTaskManager
    from .thread_control import ThreadTaskManager
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['ProcessTaskManager', 'ThreadTaskManager']
