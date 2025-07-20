# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import threading
from contextlib import contextmanager
from typing import Generator


class PauseController:
    """
    Thread-safe pause controller that allows pausing and resuming execution.

    Usage:
        controller = PauseController()
        controller.pause()   # Pauses execution
        controller.resume()  # Resumes execution
        controller.check_pause()  # Blocks if paused
    """

    def __init__(self):
        self._paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # Initially not paused
        self._lock = threading.Lock()

    def pause(self) -> None:
        """Pause execution of threads checking this controller."""
        with self._lock:
            if not self._paused:
                self._paused = True
                self._pause_event.clear()

    def resume(self) -> None:
        """Resume execution of threads checking this controller."""
        with self._lock:
            if self._paused:
                self._paused = False
                self._pause_event.set()

    def check_pause(self) -> None:
        """
        Block if paused, continue immediately if not paused.
        Call this periodically in your thread's work loop.
        """
        self._pause_event.wait()

    def is_paused(self) -> bool:
        """Return whether the controller is currently paused."""
        with self._lock:
            return self._paused


@contextmanager
def pausable() -> Generator[PauseController, None, None]:
    """
    Context manager that provides a PauseController instance.

    Example:
        with pausable() as controller:
            while True:
                controller.check_pause()
                # Do your work here
    """
    controller = PauseController()
    try:
        yield controller
    finally:
        # Ensure we resume when exiting context
        controller.resume()
