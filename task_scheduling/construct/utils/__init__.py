# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from task_scheduling.construct.utils.branch_creation import wait_branch_thread_ended, branch_thread_control, \
        wait_ended
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['wait_ended', 'wait_branch_thread_ended', 'branch_thread_control']
