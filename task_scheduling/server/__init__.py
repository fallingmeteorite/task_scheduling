# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from task_scheduling.server.server import task_server
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['task_server']
