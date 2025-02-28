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
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
        # Use thread-safe calls to shutdown
        if loop is not None:
            loop.call_soon_threadsafe(
                lambda: asyncio.create_task(shutdown(loop))
            )
            # Close the event loop
            loop.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C


async def shutdown(loop):
    # Cancel all tasks
    tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()

    # Wait for all tasks to be canceled and completed
    await asyncio.gather(*tasks, return_exceptions=True)
    # Stop the event loop
    loop.stop()
