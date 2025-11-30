# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Task scheduling system startup script.

This script starts the proxy server for the task scheduling system
and handles graceful shutdown on keyboard interrupt.
"""

from task_scheduling.proxy_server import proxy_server


if __name__ == "__main__":
    try:
        proxy_server.start()
    except KeyboardInterrupt:
        proxy_server.stop()