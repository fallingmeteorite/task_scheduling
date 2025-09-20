# -*- coding: utf-8 -*-
# Author: fallingmeteorite

import os
import signal
import sys

from ..common import logger


def worker_initializer():
    """
    Clean up resources when the program exits.
    """

    def signal_handler(signum, frame):
        logger.debug(f"Worker {os.getpid()} received signal, exiting...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # termination signal
