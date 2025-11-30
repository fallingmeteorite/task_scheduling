# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""

import sys

# Prevent errors during multi-process initialization
try:
    from task_scheduling.proxy_server.proxy import proxy_server
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['proxy_server']
