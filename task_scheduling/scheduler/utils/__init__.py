# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from task_scheduling.scheduler.utils.end_cleaning import exit_cleanup
    from task_scheduling.scheduler.utils.info_share import SharedStatusInfo
    from task_scheduling.scheduler.utils.priority_check import TaskCounter
    from task_scheduling.scheduler.utils.parameter_check import get_param_count, retry_on_error_decorator_check
    from task_scheduling.scheduler.utils.dill_coverage import DillProcessPoolExecutor
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['exit_cleanup', 'SharedStatusInfo', 'TaskCounter', 'get_param_count', 'retry_on_error_decorator_check', 'DillProcessPoolExecutor']
