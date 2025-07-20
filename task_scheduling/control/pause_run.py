# -*- coding: utf-8 -*-
# Author: fallingmeteorite

import threading
import ctypes
import platform
from contextlib import contextmanager
from typing import Dict
from ..common import logger


class ThreadController:
    """Simplified thread controller, fully controlled through context management"""

    def __init__(self):
        self._handles: Dict[int, int] = {}
        self._lock = threading.Lock()
        self._setup_platform()

    def _setup_platform(self):
        """Initialize platform-specific settings"""
        self.platform = platform.system()

        if self.platform == "Windows":
            self._kernel32 = ctypes.windll.kernel32
            self.THREAD_ACCESS = 0x0002  # THREAD_SUSPEND_RESUME
        elif self.platform in ("Linux", "Darwin"):
            lib_name = "libc.so.6" if self.platform == "Linux" else "libSystem.dylib"
            self._libc = ctypes.CDLL(lib_name)
        else:
            raise NotImplementedError(f"Unsupported platform: {self.platform}")

    @contextmanager
    def control_context(self):
        """Thread control context manager"""
        current_thread = threading.current_thread()
        tid = current_thread.ident
        if tid is None:
            raise RuntimeError("Thread not started")

        # Register thread
        if not self._register_thread(tid):
            raise RuntimeError("Failed to register thread")

        # Create control interface
        controller = _ThreadControl(self, tid)

        try:
            yield controller
        finally:
            # Unregister thread
            self._unregister_thread(tid)

    def _register_thread(self, tid: int) -> bool:
        """Internal method: Register a thread"""
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
            except Exception as e:
                logger.error(f"Failed to register thread {tid}: {e}")
                return False

    def _unregister_thread(self, tid: int) -> bool:
        """Internal method: Unregister a thread"""
        with self._lock:
            if tid not in self._handles:
                return False

            try:
                if self.platform == "Windows":
                    self._kernel32.CloseHandle(self._handles[tid])
                del self._handles[tid]
                return True
            except Exception as e:
                logger.error(f"Failed to unregister thread {tid}: {e}")
                return False

    def _pause_thread(self, tid: int) -> bool:
        """Internal method: Pause a thread"""
        with self._lock:
            if tid not in self._handles:
                return False

            try:
                if self.platform == "Windows":
                    if self._kernel32.SuspendThread(self._handles[tid]) == -1:
                        raise ctypes.WinError()
                else:
                    if self._libc.pthread_kill(tid, 19) != 0:  # SIGSTOP
                        raise RuntimeError("Failed to pause thread")
                return True
            except Exception as e:
                logger.error(f"Failed to pause thread {tid}: {e}")
                return False

    def _resume_thread(self, tid: int) -> bool:
        """Internal method: Resume a thread"""
        with self._lock:
            if tid not in self._handles:
                return False

            try:
                if self.platform == "Windows":
                    if self._kernel32.ResumeThread(self._handles[tid]) == -1:
                        raise ctypes.WinError()
                else:
                    if self._libc.pthread_kill(tid, 18) != 0:  # SIGCONT
                        raise RuntimeError("Failed to resume thread")
                return True
            except Exception as e:
                logger.error(f"Failed to resume thread {tid}: {e}")
                return False


class _ThreadControl:
    """Thread control interface (for internal use only)"""

    def __init__(self, controller: ThreadController, tid: int):
        self._controller = controller
        self._tid = tid
        self._paused = False

    def pause(self):
        """Pause the current thread"""
        if self._paused:
            raise RuntimeError("Thread already paused")

        if self._controller._pause_thread(self._tid):
            self._paused = True
        else:
            raise RuntimeError("Failed to pause thread")

    def resume(self):
        """Resume the current thread (to be called from another thread)"""
        if not self._paused:
            raise RuntimeError("Thread not paused")

        if self._controller._resume_thread(self._tid):
            self._paused = False
        else:
            raise RuntimeError("Failed to resume thread")

    @property
    def is_paused(self) -> bool:
        """Check if thread is paused"""
        return self._paused