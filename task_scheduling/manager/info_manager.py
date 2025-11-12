# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Thread-safe shared dictionary for task management.

This module provides a thread-safe dictionary implementation for sharing
task information across multiple threads.
"""
import threading

from typing import Any, Dict


class SharedTaskDict:
    """
    Thread-safe shared dictionary created at instantiation
    """

    def __init__(self):
        """
        Initialize with an empty dictionary that will be shared among threads
        """
        self._tasks: Dict[str, Any] = {}  # Dictionary created at instantiation
        self._lock = threading.RLock()  # Lock for thread safety

    def write(self, task_name: str, task_id: Any) -> bool:
        """
        Write a task to the shared dictionary

        Args:
            task_name: Task name
            task_id: Task ID

        Returns:
            bool: True if new task, False if updating existing task
        """
        with self._lock:
            is_new = task_name not in self._tasks
            self._tasks[task_name] = task_id
            return is_new

    def read(self, task_name: str = None) -> Any:
        """
        Read from the shared dictionary

        Args:
            task_name: If provided, read specific task; if None, read entire dictionary

        Returns:
            If task_name provided: task ID if exists, None otherwise
            If task_name None: copy of entire dictionary
        """
        with self._lock:
            if task_name is not None:
                return self._tasks.get(task_name)
            else:
                return self._tasks.copy()
