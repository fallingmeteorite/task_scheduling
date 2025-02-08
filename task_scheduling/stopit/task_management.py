# -*- coding: utf-8 -*-
from typing import Dict, Any

from ..common import logger


class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def add(self, cancel_obj: Any, skip_obj: Any, terminate_obj: Any, task_id: str) -> None:
        """
        Add task control objects to the dictionary.

        :param cancel_obj: An object that has a cancel method.
        :param skip_obj: An object that has a skip method.
        :param terminate_obj: An object that has a terminate method.
        :param task_id: Task ID, used as the key in the dictionary.
        """
        if task_id in self.tasks:
            logger.warning(f"Task with task_id '{task_id}' already exists, overwriting")
        self.tasks[task_id] = {
            'cancel': cancel_obj,
            'skip': skip_obj,
            'terminate': terminate_obj
        }

    def remove(self, task_id: str) -> None:
        """
        Remove the task and its associated data from the dictionary based on task_id.

        :param task_id: Task ID.
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
        else:
            logger.warning(f"No task found with task_id '{task_id}', operation invalid")

    def check(self, task_id: str) -> bool:
        """
        Check if the given task_id exists in the dictionary.

        :param task_id: Task ID.
        :return: True if the task_id exists, otherwise False.
        """
        return task_id in self.tasks

    def _execute_operation(self, task_id: str, operation: str) -> None:
        """
        Execute the specified operation for the task_id.

        :param task_id: Task ID.
        :param operation: Operation type, can be 'cancel', 'skip', or 'terminate'.
        """
        if task_id in self.tasks:
            operation_obj = self.tasks[task_id][operation]
            if operation_obj is not None:
                try:
                    getattr(operation_obj, operation)()
                except Exception as error:
                    logger.error(f"Failed to {operation} task with task_id '{task_id}': {error}")
            else:
                logger.warning(f"{operation} for task_id '{task_id}' is None, cannot execute {operation} operation")
        else:
            logger.warning(f"No task found with task_id '{task_id}', operation invalid")

    def cancel_task(self, task_id: str) -> None:
        """
        Cancel the task based on task_id.

        :param task_id: Task ID.
        """
        self._execute_operation(task_id, 'cancel')

    def cancel_all_tasks(self) -> None:
        """
        Cancel all tasks in the dictionary.
        """
        for task_id in self.tasks:
            self.cancel_task(task_id)

    def skip_task(self, task_id: str) -> None:
        """
        Skip the task based on task_id.

        :param task_id: Task ID.
        """
        self._execute_operation(task_id, 'skip')

    def skip_all_tasks(self) -> None:
        """
        Skip all tasks in the dictionary.
        """
        for task_id in self.tasks:
            self.skip_task(task_id)

    def terminate_task(self, task_id: str) -> None:
        """
        Terminate the task based on task_id.

        :param task_id: Task ID.
        """
        self._execute_operation(task_id, 'terminate')

    def terminate_all_tasks(self) -> None:
        """
        Terminate all tasks in the dictionary.
        """
        for task_id in self.tasks:
            self.terminate_task(task_id)
