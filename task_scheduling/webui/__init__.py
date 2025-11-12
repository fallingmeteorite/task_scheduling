# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from .control_ui import start_task_status_ui, get_tasks_info
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['start_task_status_ui', 'get_tasks_info']
