# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from .details_manager import task_status_manager
    from .info_manager import SharedTaskDict
    from .scheduler_manager import task_scheduler
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['task_status_manager', 'SharedTaskDict', 'task_scheduler']
