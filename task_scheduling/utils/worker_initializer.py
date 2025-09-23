# -*- coding: utf-8 -*-
# Author: fallingmeteorite

import os
import signal
import sys
import threading

from ..common import logger


def worker_initializer():
    """
    Used to fix the error that occurs when ending a task after the process is recycled.
    """

    def signal_handler(signum, frame):
        if threading.active_count() == 1:
            logger.debug(f"Worker {os.getpid()}. Perform cleaning")
            sys.exit(0)
        else:
            logger.warning(f"Worker {os.getpid()}. There are tasks that have not been completed, and they will be forcibly terminated.")

    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # termination signal
