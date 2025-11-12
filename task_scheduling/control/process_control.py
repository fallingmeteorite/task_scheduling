# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Process Task Management System.

This module provides a thread-safe process task manager that handles task lifecycle
operations including pause, resume, and termination. It features a monitoring system
that processes control commands from a shared task queue in real-time.

The manager is designed to work with multiprocessing tasks and provides:
- Thread-safe task operations using RLock
- Automatic task failure detection and cleanup
- Platform-specific pause/resume functionality (Windows only)
- Graceful task termination with pre-resume handling

Key Components:
    ProcessTaskManager: Main class for managing process tasks with monitoring capabilities
"""
import threading
import time
import platform

from typing import Dict, Any, Union


class ProcessTaskManager:
    """
    Thread-safe manager for controlling task processes with pause, resume, and terminate capabilities.
    Monitors a task queue for control commands and applies them to managed tasks.
    """

    __slots__ = ['_tasks', '_lock', '_task_queue', '_running', '_main_task_id', '_fail_count_dict']

    def __init__(self, task_queue: Dict) -> None:
        """
        Initialize the ProcessTaskManager.

        Args:
            task_queue: Shared dictionary for receiving task control commands
        """
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._task_queue = task_queue
        self._running = True
        self._main_task_id: Union[str, None] = None
        self._fail_count_dict: dict = {}

        # Start monitor thread
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def add(self, terminate_obj: Any, pause_ctx: Any, task_id: str) -> None:
        """
        Add task control objects to the manager.

        Args:
            terminate_obj: Object with terminate method for stopping the task
            pause_ctx: Object with pause/resume methods for controlling task execution
            task_id: Unique identifier for the task
        """
        with self._lock:
            if task_id in self._tasks:
                # Update existing task
                if terminate_obj:
                    self._tasks[task_id]['terminate'] = terminate_obj
                if pause_ctx:
                    self._tasks[task_id]['pause'] = pause_ctx
            else:
                # Create new task entry
                self._tasks[task_id] = {'terminate': terminate_obj, 'pause': pause_ctx}
                # Set as main task if this is the first task
                if self._main_task_id is None:
                    self._main_task_id = task_id

    def remove(self, task_id: str) -> None:
        """
        Remove a task from the manager.

        Args:
            task_id: Unique identifier for the task to remove
        """
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                # Update main task if needed
                if task_id == self._main_task_id:
                    self._running = False

    def exists(self, task_id: str) -> bool:
        """
        Check if a task exists in the manager.

        Args:
            task_id: Unique identifier for the task

        Returns:
            bool: True if task exists, False otherwise
        """
        with self._lock:
            return task_id in self._tasks

    def _execute_operation(self, task_id: str, op_type: str, method: str) -> None:
        """
        Execute operation on task with error handling.

        Args:
            task_id: Task identifier
            op_type: Operation type key in task dict
            method: Method name to call
        """
        with self._lock:
            if task_id not in self._tasks:
                return

            obj = self._tasks[task_id].get(op_type)
            if obj is not None and hasattr(obj, method):
                try:
                    getattr(obj, method)()
                except (RuntimeError, Exception):
                    pass  # Ignore all exceptions

    def terminate_branch_tasks(self) -> None:
        """Terminate all tasks except the main task."""
        with self._lock:
            for task_id in list(self._tasks.keys()):
                if task_id != self._main_task_id:
                    self.terminate_task(task_id)
                    del self._tasks[task_id]

    def terminate_task(self, task_id: str) -> None:
        """Terminate specific task."""
        # Resume before terminating to ensure clean shutdown
        self.resume_task(task_id)
        self._execute_operation(task_id, 'terminate', 'terminate')

    def pause_task(self, task_id: str) -> None:
        """Pause specific task."""
        if platform.system() == "Windows":
            self._execute_operation(task_id, 'pause', 'pause')

    def resume_task(self, task_id: str) -> None:
        """Resume specific task."""
        if platform.system() == "Windows":
            self._execute_operation(task_id, 'pause', 'resume')

    def _monitor_loop(self) -> None:
        """Monitor the task queue for control commands and process them."""
        MAX_FAIL_COUNT = 5  # Maximum failure threshold

        while self._running:
            try:
                if not self._task_queue:
                    time.sleep(0.01)
                    continue

                # Create a copy of items to avoid modification during iteration
                items_copy = list(self._task_queue.items())
                for task_id, actions in items_copy:
                    if not self.exists(task_id):
                        # Initialize or increase the failure count
                        if task_id not in self._fail_count_dict:
                            self._fail_count_dict[task_id] = 1
                        else:
                            self._fail_count_dict[task_id] += 1
                            # If the maximum number of failures is exceeded, perform cleanup
                            if self._fail_count_dict[task_id] >= MAX_FAIL_COUNT:
                                # Remove this nonexistent task from the task queue
                                if task_id in self._task_queue:
                                    del self._task_queue[task_id]
                                # Remove from failure count
                                if task_id in self._fail_count_dict:
                                    del self._fail_count_dict[task_id]
                        continue

                    # Process each action in sequence
                    for action in actions:
                        # Directly call the corresponding method
                        if action == "kill":
                            self.terminate_task(task_id)
                        elif action == "pause":
                            self.pause_task(task_id)
                        elif action == "resume":
                            self.resume_task(task_id)
                    # Remove from queue since we're processing it
                    del self._task_queue[task_id]

                time.sleep(0.01)
            except (BrokenPipeError, EOFError):
                break
