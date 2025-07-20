# -*- coding: utf-8 -*-
# Author: fallingmeteorite

import threading
from typing import Dict, Any

from ..common import logger


class ThreadTaskManager:
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()  # Use a lock to control concurrent operations

    def add(self, cancel_obj: Any, skip_obj: Any, pause_ctx: Any, task_id: str) -> None:
        """
        Add task control objects to the dictionary.

        :param cancel_obj: An object that has a cancel method.
        :param skip_obj: An object that has a skip method.
        :param pause_ctx: An object that has a pause method.
        :param task_id: Task ID, used as the key in the dictionary.
        """
        with self._lock:  # Acquire the lock to ensure thread-safe operations
            if task_id in self._tasks:
                logger.warning(f"Task with task_id '{task_id}' already exists, overwriting")
            self._tasks[task_id] = {
                'cancel': cancel_obj,
                'skip': skip_obj,
                'pause': pause_ctx
            }

    def remove(self, task_id: str) -> None:
        """
        Remove the task and its associated data from the dictionary based on task_id.

        :param task_id: Task ID.
        """
        if task_id in self._tasks:
            del self._tasks[task_id]
        else:
            logger.warning(f"No task found with task_id '{task_id}', operation invalid")

    def check(self, task_id: str) -> bool:
        """
        Check if the given task_id exists in the dictionary.

        :param task_id: Task ID.
        :return: True if the task_id exists, otherwise False.
        """
        with self._lock:  # Acquire the lock to ensure thread-safe operations
            return task_id in self._tasks

    def cancel_task(self, task_id: str) -> None:
        """
        Cancel the task based on task_id.

        :param task_id: Task ID.
        """
        with self._lock:  # Acquire the lock to ensure thread-safe operations
            if task_id in self._tasks:
                try:
                    self._tasks[task_id]['cancel'].cancel()
                except Exception as error:
                    logger.error(error)
            else:
                logger.warning(f"No task found with task_id '{task_id}', operation invalid")

    def cancel_all_tasks(self) -> None:
        """
        Cancel all tasks in the dictionary.
        """
        for task_id in list(
                self._tasks.keys()):  # Use list(self._tasks.keys()) to avoid errors due to dictionary size changes
            self.cancel_task(task_id)

    def skip_task(self, task_id: str) -> None:
        """
        Skip the task based on task_id.

        :param task_id: Task ID.
        """
        with self._lock:  # Acquire the lock to ensure thread-safe operations
            if task_id in self._tasks:
                try:
                    self._tasks[task_id]['skip'].skip()
                except Exception as error:
                    logger.error(error)
            else:
                logger.warning(f"No task found with task_id '{task_id}', operation invalid")

    def skip_all_tasks(self) -> None:
        """
        Skip all tasks in the dictionary.
        """
        for task_id in list(
                self._tasks.keys()):  # Use list(self._tasks.keys()) to avoid errors due to dictionary size changes
            self.skip_task(task_id)

    def pause_task(self, task_id: str) -> None:
        """
        Pause the task based on task_id.

        :param task_id: Task ID.
        """
        with self._lock:  # Acquire the lock to ensure thread-safe operations
            if task_id in self._tasks:
                try:
                    self._tasks[task_id]['pause'].pause()
                except Exception as error:
                    logger.error(error)
            else:
                logger.warning(f"No task found with task_id '{task_id}', operation invalid")

    def resume_task(self, task_id: str) -> None:
        """
        Resume the task based on task_id.

        :param task_id: Task ID.
        """
        with self._lock:  # Acquire the lock to ensure thread-safe operations
            if task_id in self._tasks:
                try:
                    self._tasks[task_id]['pause'].resume()
                except Exception as error:
                    logger.error(error)
            else:
                logger.warning(f"No task found with task_id '{task_id}', operation invalid")
