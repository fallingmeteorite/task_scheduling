# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from task_scheduling.result_server.get_service import result_server
    from task_scheduling.result_server.get_result import get_task_result
    from task_scheduling.result_server.upload import store_task_result
except KeyboardInterrupt:
    sys.exit(0)
__all__ = ['result_server', 'get_task_result', 'store_task_result']
