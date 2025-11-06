# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import os
import threading
import time
from typing import Dict, Any, List

from ..common import logger, config


class ProcessTaskManager:
    """
    A thread-safe manager for controlling task processes with pause, resume, and terminate capabilities.
    Monitors a task queue for control commands and applies them to managed tasks.
    """

    __slots__ = [
        '_tasks',
        '_operation_lock',
        '_task_queue',
        '_start',
        '_main_task_id'
    ]

    def __init__(self, task_queue: Dict) -> None:
        """
        Initialize the ProcessTaskManager.

        Args:
            task_queue: Shared dictionary for receiving task control commands
        """
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._operation_lock = threading.RLock()  # Use RLock for nested lock acquisition
        self._task_queue = task_queue
        self._start: bool = True
        self._main_task_id: str = None

        self._start_monitor_thread()

    def add(self, terminate_obj: Any, pause_ctx: Any, task_id: str) -> None:
        """
        Add task control objects to the manager.

        Args:
            terminate_obj: Object with a terminate method for stopping the task
            pause_ctx: Object with pause/resume methods for controlling task execution
            task_id: Unique identifier for the task
        """
        with self._operation_lock:
            if task_id in self._tasks:
                # Update existing task
                if terminate_obj is not None:
                    self._tasks[task_id]['terminate'] = terminate_obj
                if pause_ctx is not None:
                    self._tasks[task_id]['pause'] = pause_ctx
            else:
                # Create new task entry
                self._tasks[task_id] = {
                    'terminate': terminate_obj,
                    'pause': pause_ctx
                }
                # Set as main task if this is the first task
                if self._main_task_id is None:
                    self._main_task_id = task_id
                    logger.debug(f"Main task set to: {task_id}")

    def remove(self, task_id: str) -> None:
        """
        Remove a task from the manager.

        Args:
            task_id: Unique identifier for the task to remove
        """
        with self._operation_lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                logger.debug(f"Task {task_id} removed from manager")

                # Update main task if needed
                if task_id == self._main_task_id:
                    self._main_task_id = self._get_new_main_task_id()

                # Stop monitor if no tasks remaining
                if not self._tasks:
                    logger.debug(f"Worker {os.getpid()} no tasks remaining, stopping monitor thread")
                    self._start = False

    def _get_new_main_task_id(self) -> str:
        """
        Get a new main task ID from remaining tasks.

        Returns:
            str: Task ID to set as new main task, or None if no tasks
        """
        return next(iter(self._tasks)) if self._tasks else None

    def check(self, task_id: str) -> bool:
        """
        Check if a task exists in the manager.

        Args:
            task_id: Unique identifier for the task

        Returns:
            bool: True if task exists, False otherwise
        """
        with self._operation_lock:
            return task_id in self._tasks

    def terminate_task(self, task_id: str) -> None:
        """
        Terminate a specific task.

        Args:
            task_id: Unique identifier for the task to terminate
        """
        with self._operation_lock:
            if task_id not in self._tasks:
                logger.warning(f"No task found with task_id '{task_id}', terminate operation invalid")
                return

            try:
                terminate_obj = self._tasks[task_id]['terminate']
                if hasattr(terminate_obj, 'terminate'):
                    terminate_obj.terminate()
                    logger.info(f"Task {task_id} terminated successfully")
                else:
                    logger.error(f"Terminate object for task {task_id} has no terminate method")
            except Exception as error:
                logger.error(f"Error terminating task '{task_id}': {error}")

    def terminate_branch_task(self) -> None:
        """
        Terminate all tasks except the main task.
        """
        with self._operation_lock:
            tasks_to_remove = []

            for task_id in list(self._tasks.keys()):
                if task_id != self._main_task_id:
                    try:
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

                        tasks_to_remove.append(task_id)
                        logger.info(f"Branch task {task_id} terminated")

                    except Exception as error:
                        logger.error(f"Error terminating branch task '{task_id}': {error}")

            # Remove terminated tasks
            for task_id in tasks_to_remove:
                if task_id in self._tasks:
                    del self._tasks[task_id]

    def pause_task(self, task_id: str) -> None:
        """
        Pause a specific task.

        Args:
            task_id: Unique identifier for the task to pause
        """
        with self._operation_lock:
            if task_id not in self._tasks:
                logger.warning(f"No task found with task_id '{task_id}', pause operation invalid")
                return

            try:
                pause_obj = self._tasks[task_id]['pause']
                if hasattr(pause_obj, 'pause'):
                    pause_obj.pause()
                    logger.info(f"Task {task_id} paused successfully")
                else:
                    logger.error(f"Pause object for task {task_id} has no pause method")
            except Exception as error:
                logger.error(f"Error pausing task '{task_id}': {error}")

    def resume_task(self, task_id: str) -> None:
        """
        Resume a paused task.

        Args:
            task_id: Unique identifier for the task to resume
        """
        with self._operation_lock:
            if task_id not in self._tasks:
                logger.warning(f"No task found with task_id '{task_id}', resume operation invalid")
                return

            try:
                pause_obj = self._tasks[task_id]['pause']
                if hasattr(pause_obj, 'resume'):
                    pause_obj.resume()
                    logger.info(f"Task {task_id} resumed successfully")
                else:
                    logger.error(f"Pause object for task {task_id} has no resume method")
            except RuntimeError:
                # Task is already running, this is not an error
                pass
            except Exception as error:
                logger.error(f"Error resuming task '{task_id}': {error}")

    def _start_monitor_thread(self) -> None:
        """Start the monitor thread for processing task control commands."""
        monitor_thread = threading.Thread(
            target=self._monitor_task_queue,
            daemon=True,
            name=f"TaskMonitor-{os.getpid()}"
        )
        monitor_thread.start()
        logger.debug("Task monitor thread started")

    def _monitor_task_queue(self) -> None:
        """Monitor the task queue for control commands and process them."""
        while self._start:
            try:
                if not self._task_queue:
                    try:
                        time.sleep(0.1)
                    except KeyboardInterrupt:
                        pass
                    continue

                # Create a copy of items to avoid modification during iteration
                items_copy = list(self._task_queue.items())[:]

                for task_id, actions in items_copy:
                    if not self.check(task_id):
                        continue

                    # Remove from queue since we're processing it
                    del self._task_queue[task_id]

                    # Process each action in sequence
                    self._process_actions(task_id, actions)

                    # Check if we should stop monitoring
                    with self._operation_lock:
                        if not self._tasks:
                            logger.debug(f"Worker {os.getpid()} no tasks remaining, stopping monitor")
                            self._start = False
                            break

            except (IndexError, KeyError):
                # Race condition in queue access, continue normally
                pass
            except Exception as error:
                logger.error(f"Error in monitor thread: {error}")
                try:
                    time.sleep(0.1)  # Prevent tight error loop
                except KeyboardInterrupt:
                    pass

    def _process_actions(self, task_id: str, actions: List[str]) -> None:
        """
        Process a list of actions for a specific task.

        Args:
            task_id: Task identifier
            actions: List of actions to perform
        """
        action_handlers = {
            "kill": self.terminate_task,
            "pause": self.pause_task,
            "resume": self.resume_task
        }

        for action in actions:
            handler = action_handlers.get(action)
            if handler:
                try:
                    handler(task_id)
                except Exception as error:
                    logger.error(f"Error executing action '{action}' for task {task_id}: {error}")
            else:
                logger.warning(f"Unknown action '{action}' for task {task_id}")
