# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Task Server startup module.

This module provides the entry point for starting the task server,
handling initialization and graceful shutdown.
"""

from task_scheduling.server import task_server


if __name__ == "__main__":
    try:
        # Start the server
        task_server.start()
    except KeyboardInterrupt:
        # Handle user interrupt signal for graceful server shutdown
        task_server.stop()