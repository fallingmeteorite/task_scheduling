# -*- coding: utf-8 -*-
"""
=================
stopit.thread stop
=================

Raise asynchronous exceptions in other thread, control the timeout of blocks
or callables with a context manager or a decorator.
"""

import ctypes
import threading

from .utils import BaseTimeout, base_timetable, TimeoutException


def _async_raise(target_tid, exception):
    """Raises an asynchronous exception in another thread.
    Read http://docs.python.org/c-api/init.html#PyThreadState_SetAsyncExc
    for further enlightenment's.

    :param target_tid: target thread identifier
    :param exception: Exception class to be raised in that thread
    """
    # Ensuring and releasing GIL are useless since we're not in C
    # gil_state = ctypes.pythonapi.PyGILState_Ensure()
    ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid),
                                                     ctypes.py_object(exception))
    # ctypes.pythonapi.PyGILState_Release(gil_state)
    if ret == 0:
        raise ValueError("Invalid thread ID {}".format(target_tid))
    elif ret > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid), None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


class ThreadingTimeout(BaseTimeout):
    """Context manager for limiting the time the execution of a block
    using asynchronous threads launching exception.

    See :class:`stopit.utils.BaseTimeout` for more information
    """

    def __init__(self, seconds, swallow_exc=True):
        super(ThreadingTimeout, self).__init__(seconds, swallow_exc)
        self._state = None
        self._target_tid = threading.current_thread().ident
        self._timer = None  # PEP8

    def stop(self):
        """Called by timer thread at timeout. Raises a Timeout exception in the
        caller thread
        """
        self._state = BaseTimeout.TIMED_OUT
        _async_raise(self._target_tid, TimeoutException)

    # Required overrides
    def setup_interrupt(self):
        """Setting up the resource that interrupts the block
        """
        self._timer = threading.Timer(self._seconds, self.stop)
        self._timer.daemon = True
        self._timer.start()

    def suppress_interrupt(self):
        """Removing the resource that interrupts the block
        """
        if self._timer:
            self._timer.cancel()


class _threading_timeoutable(base_timetable):  # noqa
    """A function or method decorator that raises a ``TimeoutException`` to
    decorated functions that should not last a certain amount of time.
    This one uses ``ThreadingTimeout`` context manager.

    See :class:`.utils.base_timetable` class for further comments.
    """
    _to_ctx_mgr = ThreadingTimeout
