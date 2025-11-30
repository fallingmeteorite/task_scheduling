# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from task_scheduling.server.utils.core import TaskServerCore, task_submit
    from task_scheduling.server.utils.network import receive_message, send_message, create_health_message
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['TaskServerCore', 'task_submit', 'receive_message',
           'send_message', 'create_health_message']
