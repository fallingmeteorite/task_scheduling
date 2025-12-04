# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from task_scheduling.construct.utils.branch_creation import wait_branch_thread_ended, branch_thread_control, wait_ended
    from task_scheduling.construct.retry_task_creation import retry_on_error
    from task_scheduling.construct.quick_creation import task_group
    from task_scheduling.construct.followup_creation import task_dependency_local, task_dependency_network
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['wait_ended', 'wait_branch_thread_ended', 'branch_thread_control', 'retry_on_error', 'task_group', 'task_dependency_local', 'task_dependency_network']
