# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""

import sys

# Prevent errors during multi-process initialization
try:
    from task_scheduling.client.utils.network import send_request
    from task_scheduling.client.utils.serializer import TaskSerializer
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['send_request', 'TaskSerializer']
