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
    from task_scheduling.utils.decorator import wait_branch_thread_ended, branch_thread_control
    from task_scheduling.utils.retry import retry_on_error
    from task_scheduling.utils.check import is_async_function, wait_branch_thread_ended_check
    from task_scheduling.utils.get_result import get_task_result
    from task_scheduling.utils.upload import store_task_result
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['interruptible_sleep', 'random_name', 'wait_branch_thread_ended', 'branch_thread_control', 'retry_on_error',
           'is_async_function', 'wait_branch_thread_ended_check', 'get_task_result', 'store_task_result']
