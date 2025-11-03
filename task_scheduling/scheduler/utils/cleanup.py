# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import os
import signal
import sys
import threading


def exit_cleanup() -> None:
    """
    Used to fix the error that occurs when ending a task after the process is recycled.
    """

    def signal_handler(signum, frame):
        # Ignore the monitoring thread itself.
        if threading.active_count() <= 1:
            sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # termination signal
