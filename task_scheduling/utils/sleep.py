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
    event = threading.Event()

    def set_event():
        time.sleep(seconds)
        event.set()

    thread = threading.Thread(target=set_event, daemon=True)
    thread.start()

    while not event.is_set():
        event.wait(0.01)

    thread.join(timeout=0)
