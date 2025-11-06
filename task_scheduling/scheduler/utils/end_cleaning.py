# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import os
import signal
import sys
import threading


def exit_cleanup_liner() -> None:
    """
    Used to fix the error that occurs when ending a task after the process is recycled.
    """

    def signal_handler(signum, frame):
        """
        Signal handler for graceful process termination.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        # Ignore the monitoring thread itself.
        if threading.active_count() <= 1:
            sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal


def exit_cleanup_asyncio() -> None:
    """
    Used to fix the error that occurs when ending a task after the process is recycled.
    """

    def signal_handler(signum, frame):
        """
        Signal handler for graceful process termination.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        # Ignore the monitoring thread itself.
        if threading.active_count() <= 1:
            sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
