# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Task Server startup module.

This module provides the entry point for starting the task server,
handling initialization and graceful shutdown.
"""

import threading

from task_scheduling.control_server import RPCServer
from task_scheduling.main_server import TaskServer

if __name__ == "__main__":
    task_server = TaskServer()
    server = RPCServer()
    try:
        # Start the server
        threading.Thread(target=server.start, daemon=True).start()
        task_server.start()
    except KeyboardInterrupt:
        # Handle user interrupt signal for graceful server shutdown
        task_server.stop()
