# -*- coding: utf-8 -*-
# Author: fallingmeteorite

import ctypes
import threading
from contextlib import contextmanager


class StopException(Exception):
    """Custom timeout exception"""
    pass


def _async_raise(target_tid, exception):
    """Raise an asynchronous exception in the target thread"""
    ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid), ctypes.py_object(exception))
    if ret == 0:
        raise ValueError("Invalid thread ID {}".format(target_tid))
    elif ret > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid), None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


class _SkipContext:
    """Context object for skipping the current line"""

    def __init__(self):
        self._target_tid = threading.current_thread().ident

    def skip(self):
        """Skip the current line"""
        _async_raise(self._target_tid, StopException)


@contextmanager
def skip_on_demand():
    """Context manager that supports manual skipping of the current line"""
    _skip_ctx = _SkipContext()
    yield _skip_ctx  # Provide _skip_ctx to external code
