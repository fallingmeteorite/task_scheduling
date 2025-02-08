# -*- coding: utf-8 -*-
import uuid
from typing import Callable, List

from .common.log_config import logger
from .scheduler import io_async_task, io_liner_task
from .scheduler.utils import is_async_function


class TaskScheduler:
    __slots__ = ['ban_task_names']

    def __init__(self):
        self.ban_task_names: List[str] = []

    def add_ban_task_name(self, task_name: str) -> None:
        """
        Add a task name to the ban list.

        :param task_name: The task name to be added to the ban list.
        """
        if task_name not in self.ban_task_names:
            self.ban_task_names.append(task_name)
            logger.info(f"Task name '{task_name}' has been added to the ban list.")
        else:
            logger.warning(f"Task name '{task_name}' is already in the ban list.")

    def remove_ban_task_name(self, task_name: str) -> None:
        """
        Remove a task name from the ban list.

        :param task_name: The task name to be removed from the ban list.
        """
        if task_name in self.ban_task_names:
            self.ban_task_names.remove(task_name)
            logger.info(f"Task name '{task_name}' has been removed from the ban list.")
        else:
            logger.warning(f"Task name '{task_name}' is not in the ban list.")

    def task_creation(self, timeout_processing: bool, task_name: str, func: Callable, *args, **kwargs) -> str or None:
        """
        Add a task to the queue, choosing between asynchronous or linear task based on the function type.
        Generate a unique task ID and return it.

        :param timeout_processing: Whether to enable timeout processing.
        :param task_name: The task name.
        :param func: The task function.
        :param args: Positional arguments for the task function.
        :param kwargs: Keyword arguments for the task function.
        :return: A unique task ID.
        """
        # Check if the task name is in the ban list
        if task_name in self.ban_task_names:
            logger.warning(f"Task name '{task_name}' is banned, cannot add task.")
            return None

        # Check if func is a callable function
        if not callable(func):
            logger.warning("The provided func is not a callable function")
            return None

        # Generate a unique task ID
        task_id = str(uuid.uuid4())
        async_function = is_async_function(func)
        if async_function:
            # Add asynchronous task
            io_async_task.add_task(timeout_processing, task_name, task_id, func, *args, **kwargs)

        if not async_function:
            # Add linear task
            io_liner_task.add_task(timeout_processing, task_name, task_id, func, *args, **kwargs)


        return task_id
