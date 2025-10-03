# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import threading
import time


def interruptible_sleep(seconds: float or int) -> None:
    """
    Sleep for a specified number of seconds, but can be interrupted by setting an event.

    Args:
        seconds (float or int): Number of seconds to sleep.
    """
    _event = threading.Event()

    def set_event():
        time.sleep(seconds)
        _event.set()

    _thread = threading.Thread(target=set_event, daemon=True)
    _thread.start()

    while not _event.is_set():
        _event.wait(0.1)

    _thread.join(timeout=0)
