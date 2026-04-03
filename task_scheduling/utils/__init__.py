# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from task_scheduling.utils.sleep import interruptible_sleep
    from task_scheduling.utils.random import random_name
    from task_scheduling.utils.check import is_async_function, wait_branch_thread_ended_check
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['interruptible_sleep', 'random_name', 'is_async_function', 'wait_branch_thread_ended_check']
