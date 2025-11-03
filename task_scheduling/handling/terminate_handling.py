# -*- coding: utf-8 -*-
# Author: fallingmeteorite
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
        self.platform = platform.system()
        if self.platform == "Windows":
            self._kernel32 = ctypes.windll.kernel32
            self.THREAD_ACCESS = 0x0001 | 0x0002  # TERMINATE + SUSPEND
        elif self.platform in ("Linux", "Darwin"):
            lib_name = "libc.so.6" if self.platform == "Linux" else "libSystem.dylib"
            self._libc = ctypes.CDLL(lib_name)
        else:
            raise NotImplementedError(f"Unsupported platform: {self.platform}")

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
        """Register thread with OS"""
        with self._lock:
            if tid in self._handles:
                return True

            try:
                if self.platform == "Windows":
                    handle = self._kernel32.OpenThread(self.THREAD_ACCESS, False, tid)
                    if not handle:
                        raise ctypes.WinError()
                    self._handles[tid] = handle
                else:
                    self._handles[tid] = tid
                return True
            except Exception:
                return False

    def _unregister_thread(self, tid: int) -> bool:
        """Unregister thread from OS"""
        with self._lock:
            if tid not in self._handles:
                return False

            try:
                if self.platform == "Windows":
                    self._kernel32.CloseHandle(self._handles[tid])
                del self._handles[tid]
                return True
            except Exception:
                return False

    def raise_stop_exception(self, tid: int):
        """Raise StopException in target thread"""
        if self.platform == "Windows":
            # Use async exception on Windows
            ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(
                ctypes.c_long(tid),
                ctypes.py_object(StopException))

            if ret == 0:
                raise ValueError("Invalid thread ID")
            elif ret > 1:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
                raise SystemError("Async exception failed")
        else:
            # Use pthread_cancel on POSIX
            if self._libc.pthread_cancel(tid) != 0:
                raise RuntimeError("Failed to cancel thread")


class TerminateController:
    """Controller for terminating the current thread"""

    def __init__(self, terminator: ThreadTerminator, tid: int):
        self._terminator = terminator
        self._tid = tid

    def terminate(self):
        """Terminate the current thread by raising StopException in it"""
        self._terminator.raise_stop_exception(self._tid)
        # This line won't be reached as the thread will be terminated
