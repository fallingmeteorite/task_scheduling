# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from task_scheduling.control_server.control import RPCServer
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['RPCServer']
