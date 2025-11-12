# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Thread suspension and control utility.

This module provides a platform-agnostic way to suspend and resume threads
using context managers for safe resource management.
"""
import sys
import threading
import ctypes
import platform

from contextlib import contextmanager
from typing import Dict


class ThreadSuspender:
    """Simplified thread controller, fully controlled through context management"""

    def __init__(self):
        self._handles: Dict[int, int] = {}
        self._lock = threading.Lock()
        self._setup_platform()

    def _setup_platform(self):
        """Initialize platform-specific settings"""
        try:
            self.platform = platform.system()
        except KeyboardInterrupt:
            sys.exit(0)

        if self.platform == "Windows":
            self._kernel32 = ctypes.windll.kernel32
            self.THREAD_ACCESS = 0x0002  # THREAD_SUSPEND_RESUME
        elif self.platform in ("Linux", "Darwin"):
            pass
        else:
            raise NotImplementedError(f"Unsupported platform: {self.platform}")

    @contextmanager
    def suspend_context(self):
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

            if self.platform == "Windows":
                handle = self._kernel32.OpenThread(self.THREAD_ACCESS, False, tid)
                if not handle:
                    raise ctypes.WinError()
                self._handles[tid] = handle
            return True

    def _unregister_thread(self, tid: int) -> bool:
        """Internal method: Unregister a thread"""
        with self._lock:
            if tid not in self._handles:
                return False

            if self.platform == "Windows":
                self._kernel32.CloseHandle(self._handles[tid])
            del self._handles[tid]
            return True

    def pause_thread(self, tid: int) -> bool:
        """Internal method: Pause a thread"""
        with self._lock:
            if tid not in self._handles:
                return False

            if self.platform == "Windows":
                if self._kernel32.SuspendThread(self._handles[tid]) == -1:
                    raise ctypes.WinError()
            return True

    def resume_thread(self, tid: int) -> bool:
        """Internal method: Resume a thread"""
        with self._lock:
            if tid not in self._handles:
                return False

            if self.platform == "Windows":
                if self._kernel32.ResumeThread(self._handles[tid]) == -1:
                    raise ctypes.WinError()
            return True


class _ThreadControl:
    """Thread control interface (for internal use only)"""

    def __init__(self, controller: ThreadSuspender, tid: int):
        self._controller = controller
        self._tid = tid
        self._paused = False

    def pause(self):
        """Pause the current thread"""
        if self._paused:
            raise RuntimeError("Thread already paused")

        if self._controller.pause_thread(self._tid):
            self._paused = True
        else:
            raise RuntimeError("Failed to pause thread")

    def resume(self):
        """Resume the current thread (to be called from another thread)"""
        if not self._paused:
            raise RuntimeError("Thread not paused")

        if self._controller.resume_thread(self._tid):
            self._paused = False
        else:
            raise RuntimeError("Failed to resume thread")

    @property
    def is_paused(self) -> bool:
        """Check if thread is paused"""
        return self._paused
