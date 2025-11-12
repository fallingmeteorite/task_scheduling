# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Thread Task Management System.

This module provides a thread-safe task manager for controlling thread-based tasks
with comprehensive lifecycle management capabilities including cancellation,
termination, pause, and resume operations.

The manager is designed to work with threading tasks and provides:
- Thread-safe task operations using RLock
- Batch operations for managing multiple tasks
- Platform-specific pause/resume functionality (Windows only)
- Graceful error handling for task operations

Key Components:
    ThreadTaskManager: Main class for managing thread tasks with control capabilities
"""
import threading
import platform

from typing import Dict, Any

from ..common import logger


class ThreadTaskManager:
    """
    Thread-safe manager for task control with cancel, terminate, pause, and resume capabilities.
    """

    __slots__ = ['_tasks', '_lock']

    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def add(self, cancel_obj: Any, terminate_obj: Any, pause_ctx: Any, task_id: str) -> None:
        """
        Add task control objects to the manager.

        :param cancel_obj: Object with cancel method
        :param terminate_obj: Object with terminate method
        :param pause_ctx: Object with pause/resume methods
        :param task_id: Unique task identifier
        """
        with self._lock:
            if task_id in self._tasks:
                # Update existing task
                if terminate_obj is not None:
                    self._tasks[task_id]['terminate'] = terminate_obj
                if pause_ctx is not None:
                    self._tasks[task_id]['pause'] = pause_ctx
            else:
                # Add new task
                self._tasks[task_id] = {
                    'cancel': cancel_obj,
                    'terminate': terminate_obj,
                    'pause': pause_ctx
                }

    def remove(self, task_id: str) -> None:
        """
        Remove task from manager.

        :param task_id: Task identifier to remove
        """
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
            else:
                logger.debug(f"Task not found: {task_id}")

    def exists(self, task_id: str) -> bool:
        """
        Check if task exists in manager.

        :param task_id: Task identifier to check
        :return: True if task exists
        """
        with self._lock:
            return task_id in self._tasks

    def _execute_operation(self, task_id: str, op_type: str, method: str) -> None:
        """
        Execute operation on task with error handling.

        :param task_id: Task identifier
        :param op_type: Operation type key in task dict
        :param method: Method name to call
        """
        with self._lock:
            if task_id not in self._tasks:
                return

            try:
                getattr(self._tasks[task_id].get(op_type), method)()
            except (RuntimeError, Exception):
                pass  # Ignore all exceptions

    def cancel_all_tasks(self) -> None:
        """Cancel all tasks."""
        for task_id in list(self._tasks.keys()):
            self.resume_task(task_id)
            self.cancel_task(task_id)

    def terminate_all_tasks(self) -> None:
        """Terminate all tasks."""
        for task_id in list(self._tasks.keys()):
            self.resume_task(task_id)
            self.terminate_task(task_id)

    def resume_all_tasks(self) -> None:
        """Resume all tasks."""
        for task_id in list(self._tasks.keys()):
            self.resume_task(task_id)

    def cancel_task(self, task_id: str) -> None:
        """Cancel specific task."""
        self._execute_operation(task_id, 'cancel', 'cancel')

    def terminate_task(self, task_id: str) -> None:
        """Terminate specific task."""
        self._execute_operation(task_id, 'terminate', 'terminate')

    def pause_task(self, task_id: str) -> None:
        """Pause specific task."""
        if platform.system() == "Windows":
            self._execute_operation(task_id, 'pause', 'pause')

    def resume_task(self, task_id: str) -> None:
        """Resume specific task."""
        if platform.system() == "Windows":
            self._execute_operation(task_id, 'pause', 'resume')
