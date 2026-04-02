# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Line-by-line callback execution utility.

This module provides a context manager that executes a given callback
function on every line of code executed within the context.
"""

import sys
import time

from multiprocessing import Manager
from typing import Any


def create_shared_flag() -> Any:
    _manager = Manager()
    return _manager.Value(bool, False)


class line_tracer:
    """
    A context manager that executes a callback on each line of code.

    This class monitors code execution line by line. For every line executed
    within the context, the provided callback function is called.

    Attributes:
        original_trace: The original system trace function to restore later
    """

    def __init__(self, pause_indicator):
        """
        Initialize the line_tracer context manager.
        """
        self.pause_indicator = pause_indicator
        self.original_trace = None

    def __enter__(self):
        """
        Enter the runtime context.

        Saves the original trace function and installs a new trace
        callback that fires on every line execution.

        Returns:
            The context manager instance
        """
        # Save the original trace function to restore later
        self.original_trace = sys.gettrace()

        # Install a trace callback that invokes user callback on every line
        # CRITICAL: Always return the trace function itself (or another callable)
        sys.settrace(self._trace_callback)

        return self

    def callback(self, frame, event, arg) -> None:
        """
        Pause implementation
        """
        if self.pause_indicator.value:
            while True:
                time.sleep(0.2)
                if not self.pause_indicator.value:
                    break

    def _trace_callback(self, frame, event, arg):
        """
        Trace function called on each line/call/return event.

        Args:
            frame: Current stack frame
            event: Event type ('line', 'call', 'return', 'exception')
            arg: Event argument

        Returns:
            The trace function itself to continue tracing
        """
        # Call the user-provided callback on every event (user should filter)
        self.callback(frame, event, arg)

        # Must return a callable (itself) to keep tracing active
        return self._trace_callback

    def __exit__(self, *args):
        """
        Exit the runtime context.

        Restores the original trace function that was saved during __enter__.

        Args:
            *args: Exception type, value, and traceback (unused)
        """
        # Restore the original trace function
        sys.settrace(self.original_trace)
