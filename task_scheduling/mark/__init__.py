# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from task_scheduling.mark.mark_edit import task_function_type
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['task_function_type']