# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from .sleep import interruptible_sleep
    from .random import random_name
    from .decorator import wait_branch_thread_ended, branch_thread_control
    from .retry import retry_on_error
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['interruptible_sleep', 'random_name', 'wait_branch_thread_ended', 'branch_thread_control', 'retry_on_error']
