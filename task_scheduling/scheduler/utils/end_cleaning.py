# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Process signal handling module.

This module provides graceful process termination handling for cleanup operations
when the process receives termination signals.
"""
import signal
import sys


def exit_cleanup() -> None:
    """
    Used to fix the error that occurs when ending a task after the process is recycled.
    """

    def signal_handler(signum, _) -> None:
        """
        Signal handler for graceful process termination.

        Args:
            signum: Signal number
            _: None
        """
        try:
            # Restore the default handler and resend the signal
            signal.signal(signum, signal.SIG_DFL)
            signal.raise_signal(signum)
            sys.exit(0)
        except (KeyboardInterrupt, SystemExit):
            sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
