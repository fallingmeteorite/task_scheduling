# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from task_scheduling.rpc_server.rpc_server import RPCServer
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['RPCServer']
