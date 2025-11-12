# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Thread termination utility module.

This module provides a mechanism for gracefully terminating threads by raising
a custom StopException within the target thread's execution context.
"""
import sys
import threading
import ctypes
import platform

from contextlib import contextmanager
from typing import Dict


class StopException(Exception):
    """Custom exception for thread termination"""
    pass


class ThreadTerminator:
    """Thread terminator using context manager that raises StopException in target thread"""

    def __init__(self):
        self._handles: Dict[int, int] = {}
        self._lock = threading.Lock()
        self._setup_platform()

    def _setup_platform(self):
        try:
            self.platform = platform.system()
        except KeyboardInterrupt:
            sys.exit(0)
        # All platforms use the same asynchronous exception mechanism
        # No platform-specific handling is needed anymore

    @contextmanager
    def terminate_control(self):
        """Context manager for thread termination"""
        tid = threading.current_thread().ident
        if not tid:
            raise RuntimeError("Thread not running")

        if not self._register_thread(tid):
            raise RuntimeError("Thread registration failed")

        controller = TerminateController(self, tid)
        try:
            yield controller
        finally:
            self._unregister_thread(tid)

    def _register_thread(self, tid: int) -> bool:
        """Register thread"""
        with self._lock:
            if tid in self._handles:
                return True
            self._handles[tid] = tid
            return True

    def _unregister_thread(self, tid: int) -> bool:
        """Unregister thread"""
        with self._lock:
            if tid in self._handles:
                del self._handles[tid]
            return True

    def raise_stop_exception(self, tid: int):
        """Raise StopException in target thread using PyThreadState_SetAsyncExc"""
        # Use PyThreadState_SetAsyncExc on all platforms
        ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(tid),
            ctypes.py_object(StopException)
        )

        if ret == 0:
            # The thread may have already ended; this is not a fatal error
            return False
        elif ret > 1:
            # Clear state, but do not throw exceptions
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
            return False
        return True


class TerminateController:
    """Controller for terminating the current thread"""

    def __init__(self, terminator: ThreadTerminator, tid: int):
        self._terminator = terminator
        self._tid = tid

    def terminate(self):
        """Terminate the current thread by raising StopException in it"""
        self._terminator.raise_stop_exception(self._tid)
