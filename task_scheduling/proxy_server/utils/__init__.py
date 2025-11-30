# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""

import sys

# Prevent errors during multi-process initialization
try:
    from task_scheduling.proxy_server.utils.core import TaskManager
    from task_scheduling.proxy_server.utils.register import ServerManager
    from task_scheduling.proxy_server.utils.network import NetworkManager
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['TaskManager', 'ServerManager', 'NetworkManager']
