# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import asyncio
import os
import signal
import sys

from ..common import logger


def worker_initializer_liner():
    """
    Clean up resources when the program exits.
    """

    def signal_handler(signum, frame):
        logger.warning(f"Worker {os.getpid()} received signal, exiting...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C


def worker_initializer_asyncio():
    """
    Clean up resources when the program exits.
    """

    def signal_handler(signum, frame):
        logger.warning(f"Worker {os.getpid()} received signal, exiting...")

        loop = asyncio.get_event_loop()
        for task in asyncio.all_tasks(loop):
            task.cancel()
        loop.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
