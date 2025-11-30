# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from task_scheduling.manager.details_manager import task_status_manager
    from task_scheduling.manager.info_manager import SharedTaskDict
    from task_scheduling.manager.scheduler_manager import task_scheduler
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['task_status_manager', 'SharedTaskDict', 'task_scheduler']
