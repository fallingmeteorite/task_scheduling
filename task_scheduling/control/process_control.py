# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import threading
import time
from typing import Dict, Any

from ..common import config


class ProcessTaskManager:
    """
    Thread-safe manager for controlling task processes with pause, resume, and terminate capabilities.
    Monitors a task queue for control commands and applies them to managed tasks.
    """

    __slots__ = ['_tasks', '_lock', '_task_queue', '_running', '_main_task_id']

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
        self._main_task_id: str = None

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
                    self._main_task_id = next(iter(self._tasks)) if self._tasks else None
                # Stop monitor if no tasks remaining
                if not self._tasks:
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

    def terminate_task(self, task_id: str) -> None:
        """
        Terminate a specific task.

        Args:
            task_id: Unique identifier for the task to terminate
        """
        with self._lock:
            if task_id not in self._tasks:
                return
            terminate_obj = self._tasks[task_id].get('terminate')
            if terminate_obj and hasattr(terminate_obj, 'terminate'):
                terminate_obj.terminate()

    def terminate_branch_tasks(self) -> None:
        """Terminate all tasks except the main task."""
        with self._lock:
            for task_id in list(self._tasks.keys()):
                if task_id != self._main_task_id:
                    self._terminate_single_task(task_id)
                    del self._tasks[task_id]

    def _terminate_single_task(self, task_id: str) -> None:
        """
        Terminate a single task (internal method).

        Args:
            task_id: Unique identifier for the task to terminate
        """
        if config.get("thread_management", False):
            # Resume before terminating to ensure clean shutdown
            pause_obj = self._tasks[task_id].get('pause')
            if pause_obj and hasattr(pause_obj, 'resume'):
                try:
                    pause_obj.resume()
                except RuntimeError:
                    pass  # Already running, ignore
            # Terminate the task
            terminate_obj = self._tasks[task_id].get('terminate')
            if terminate_obj and hasattr(terminate_obj, 'terminate'):
                terminate_obj.terminate()

    def pause_task(self, task_id: str) -> None:
        """
        Pause a specific task.

        Args:
            task_id: Unique identifier for the task to pause
        """
        self._control_task(task_id, 'pause')

    def resume_task(self, task_id: str) -> None:
        """
        Resume a paused task.

        Args:
            task_id: Unique identifier for the task to resume
        """
        self._control_task(task_id, 'resume')

    def _control_task(self, task_id: str, action: str) -> None:
        """
        Control task pause/resume (internal method).

        Args:
            task_id: Unique identifier for the task
            action: Action to perform ('pause' or 'resume')
        """
        with self._lock:
            if task_id not in self._tasks:
                return
            pause_obj = self._tasks[task_id].get('pause')
            if pause_obj and hasattr(pause_obj, action):
                try:
                    getattr(pause_obj, action)()
                except RuntimeError:
                    pass  # Already in desired state

    def _monitor_loop(self) -> None:
        """Monitor the task queue for control commands and process them."""
        while self._running:
            try:
                if not self._task_queue:
                    time.sleep(0.01)
                    continue
                # Create a copy of items to avoid modification during iteration
                items_copy = list(self._task_queue.items())[:]
                for task_id, actions in items_copy:
                    if not self.exists(task_id):
                        continue
                    # Remove from queue since we're processing it
                    del self._task_queue[task_id]
                    # Process each action in sequence
                    for action in actions:
                        self._execute_action(task_id, action)

                time.sleep(0.01)
            except (BrokenPipeError, EOFError):
                break

    def _execute_action(self, task_id: str, action: str) -> None:
        """
        Execute a single action for a task.

        Args:
            task_id: Task identifier
            action: Action to perform
        """
        action_handlers = {
            "kill": self.terminate_task,
            "pause": self.pause_task,
            "resume": self.resume_task
        }
        if action in action_handlers:
            action_handlers[action](task_id)
