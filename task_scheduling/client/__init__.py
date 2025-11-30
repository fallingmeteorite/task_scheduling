# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""

import sys

# Prevent errors during multi-process initialization
try:
    from task_scheduling.client.client import submit_function_task
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['submit_function_task']
