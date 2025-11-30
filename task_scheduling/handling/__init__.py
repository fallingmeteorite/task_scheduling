# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from task_scheduling.handling.pause_handling import ThreadSuspender
    from task_scheduling.handling.timeout_handling import ThreadingTimeout, TimeoutException
    from task_scheduling.handling.terminate_handling import ThreadTerminator, StopException
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['ThreadSuspender', 'ThreadTerminator', 'StopException', 'TimeoutException', 'ThreadingTimeout']
