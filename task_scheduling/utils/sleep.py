# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Interruptible sleep utility for responsive thread management.

This module provides a sleep function that can be interrupted, allowing for
more responsive thread control compared to standard time.sleep().
"""

import threading
import time

from typing import Union


def interruptible_sleep(seconds: Union[float, int]) -> None:
    """
    Sleep for a specified number of seconds with interrupt capability.

    This function provides a more responsive alternative to time.sleep() by
    breaking the sleep into smaller intervals and checking for interruption
    signals. Useful for threads that need to be responsive to external events.

    Args:
        seconds: Number of seconds to sleep. Can be a float for sub-second precision.

    Example:
        >>> interruptible_sleep(5.5)  # Sleep for 5.5 seconds
        >>> # Can be interrupted by setting the internal event if needed
    """
    _event = threading.Event()

    def set_event():
        """Internal function to set the event after specified seconds."""
        time.sleep(seconds)
        _event.set()

    # Start a daemon thread to set the event after the sleep duration
    _thread = threading.Thread(target=set_event, daemon=True)
    _thread.start()

    # Wait in small intervals to allow for potential interruption
    while not _event.is_set():
        _event.wait(0.1)

    # Clean up the thread
    _thread.join(timeout=0)
