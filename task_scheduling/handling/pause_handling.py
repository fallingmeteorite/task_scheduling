# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Line-by-line callback execution utility with multiprocessing.Value fast flag.

This module provides a context manager that executes a given callback
function on every line of code executed within the context. The pause
indicator is a multiprocessing.Event that can be shared across processes,
allowing external processes to pause/resume tracing without busy-waiting.

Performance optimization:
    Uses a multiprocessing.Value('b') as a fast atomic flag to check the
    paused state. In non-paused state, the trace callback only performs
    one integer comparison and returns immediately, avoiding Event method
    overhead. When paused, it falls back to Event.wait() for zero-CPU blocking.
"""

import sys
import multiprocessing


class ThreadSuspender:
    """
    A context manager that executes a callback on each line of code.

    This class monitors code execution line by line. For every line executed
    within the context, the provided callback function is called.

    The context manager provides a multiprocessing.Event pause indicator
    that can be used to pause/resume tracing from another process or thread.
    Unlike the Value-based approach, this implementation uses Event.wait()
    to block with zero CPU usage while paused.

    Attributes:
        pause_indicator: A multiprocessing.Event object. Call clear() to pause,
                         set() to resume. Initially set (not paused).
        original_trace: The original system trace function to restore later.
    """
    __slots__ = ('pause_indicator', '_fast_flag', 'original_trace')

    def __init__(self):
        """
        Initialize the line_tracer context manager.

        Creates a multiprocessing.Event and a fast atomic flag (Value('b'))
        for low-overhead paused-state checking.
        """
        # Event for cross-process blocking (zero CPU when paused)
        self.pause_indicator = multiprocessing.Event()
        self.pause_indicator.set()  # Initially not paused

        # Fast atomic flag: 1 = running, 0 = paused.
        # Use lock=False to avoid mutex overhead on every read (atomic for 'b')
        self._fast_flag = multiprocessing.Value('b', 1, lock=False)

        self.original_trace = None

    def __enter__(self):
        """
        Enter the runtime context.

        Saves the original trace function and installs a new trace
        callback that fires on every line execution.

        Returns:
            The multiprocessing.Event pause indicator. External processes
            can call clear() to pause tracing, set() to resume.
        """
        self.original_trace = sys.gettrace()

        # Bind fast flag and event as local variables via default arguments
        # to avoid closure lookup overhead.
        fast_flag = self._fast_flag
        pause_event = self.pause_indicator

        def trace_callback(frame, event, arg, ff=fast_flag, pe=pause_event, _self=None):
            # Fast path: only block when paused and the event is a line event.
            # The condition is ordered to short-circuit on ff.value != 0,
            # avoiding the event type comparison in the common running state.
            if event == 'line':
                if ff.value == 0:
                    # Slow path: paused, block until resumed (zero CPU while blocked)
                    pe.wait()
            return _self

        # Bind the callback to itself as a default argument to avoid free variable lookup
        trace_callback.__defaults__ = (fast_flag, pause_event, trace_callback)

        sys.settrace(trace_callback)

        # Override clear() and set() of the returned Event to keep fast flag in sync.
        # This ensures external processes can still use the Event interface.
        original_clear = self.pause_indicator.clear
        original_set = self.pause_indicator.set

        def patched_clear():
            original_clear()
            fast_flag.value = 0

        def patched_set():
            original_set()
            fast_flag.value = 1

        self.pause_indicator.clear = patched_clear
        self.pause_indicator.set = patched_set

        return self.pause_indicator

    def __exit__(self, *args):
        """
        Exit the runtime context.

        Restores the original trace function that was saved during __enter__.

        Args:
            *args: Exception type, value, and traceback (unused).
        """
        sys.settrace(self.original_trace)


# Can only run properly on the Windows platform!
# import ctypes
# import platform
# import sys
# import threading
# from contextlib import contextmanager
# from typing import Dict
#
#
# class ThreadSuspender:
#     """Simplified thread controller, fully controlled through context management"""
#
#     def __init__(self):
#         self._handles: Dict[int, int] = {}
#         self._lock = threading.Lock()
#         self._setup_platform()
#
#     def _setup_platform(self):
#         """Initialize platform-specific settings"""
#         try:
#             self.platform = platform.system()
#         except KeyboardInterrupt:
#             sys.exit(0)
#
#         if self.platform == "Windows":
#             self._kernel32 = ctypes.windll.kernel32
#             self.THREAD_ACCESS = 0x0002  # THREAD_SUSPEND_RESUME
#         elif self.platform in ("Linux", "Darwin"):
#             pass
#         else:
#             raise NotImplementedError(f"Unsupported platform: {self.platform}")
#
#     @contextmanager
#     def suspend_context(self):
#         """Thread control context manager"""
#         current_thread = threading.current_thread()
#         tid = current_thread.ident
#         if tid is None:
#             raise RuntimeError("Thread not started")
#
#         # Register thread
#         if not self._register_thread(tid):
#             raise RuntimeError("Failed to register thread")
#
#         # Create control interface
#         controller = _ThreadControl(self, tid)
#
#         try:
#             yield controller
#         finally:
#             # Unregister thread
#             self._unregister_thread(tid)
#
#     def _register_thread(self, tid: int) -> bool:
#         """Internal method: Register a thread"""
#         with self._lock:
#             if tid in self._handles:
#                 return True
#
#             if self.platform == "Windows":
#                 handle = self._kernel32.OpenThread(self.THREAD_ACCESS, False, tid)
#                 if not handle:
#                     raise ctypes.WinError()
#                 self._handles[tid] = handle
#             return True
#
#     def _unregister_thread(self, tid: int) -> bool:
#         """Internal method: Unregister a thread"""
#         with self._lock:
#             if tid not in self._handles:
#                 return False
#
#             if self.platform == "Windows":
#                 self._kernel32.CloseHandle(self._handles[tid])
#             del self._handles[tid]
#             return True
#
#     def pause_thread(self, tid: int) -> bool:
#         """Internal method: Pause a thread"""
#         with self._lock:
#             if tid not in self._handles:
#                 return False
#
#             if self.platform == "Windows":
#                 if self._kernel32.SuspendThread(self._handles[tid]) == -1:
#                     raise ctypes.WinError()
#             return True
#
#     def resume_thread(self, tid: int) -> bool:
#         """Internal method: Resume a thread"""
#         with self._lock:
#             if tid not in self._handles:
#                 return False
#
#             if self.platform == "Windows":
#                 if self._kernel32.ResumeThread(self._handles[tid]) == -1:
#                     raise ctypes.WinError()
#             return True
#
#
# class _ThreadControl:
#     """Thread control interface (for internal use only)"""
#
#     def __init__(self, controller: ThreadSuspender, tid: int):
#         self._controller = controller
#         self._tid = tid
#         self._paused = False
#
#     def pause(self):
#         """Pause the current thread"""
#         if self._paused:
#             raise RuntimeError("Thread already paused")
#
#         if self._controller.pause_thread(self._tid):
#             self._paused = True
#         else:
#             raise RuntimeError("Failed to pause thread")
#
#     def resume(self):
#         """Resume the current thread (to be called from another thread)"""
#         if not self._paused:
#             raise RuntimeError("Thread not paused")
#
#         if self._controller.resume_thread(self._tid):
#             self._paused = False
#         else:
#             raise RuntimeError("Failed to resume thread")
#
#     @property
#     def is_paused(self) -> bool:
#         """Check if thread is paused"""
#         return self._paused
