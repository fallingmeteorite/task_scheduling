# -*- coding: utf-8 -*-
import uuid
from typing import Callable

from .common.log_config import logger
from .scheduler.utils import is_async_function
from .scheduler_management import task_scheduler

def task_creation(function_type: str, timeout_processing: bool, task_name: str, func: Callable, *args,
                  **kwargs) -> str or None:
    """
    Add a task to the queue, choosing between asynchronous or linear task based on the function type.
    Generate a unique task ID and return it.

    :param function_type:The type of the function.
    :param timeout_processing: Whether to enable timeout processing.
    :param task_name: The task name.
    :param func: The task function.
    :param args: Positional arguments for the task function.
    :param kwargs: Keyword arguments for the task function.
    :return: A unique task ID.
    """
    # Check if func is a callable function
    if not callable(func):
        logger.warning("The provided func is not a callable function")
        return None

    # Generate a unique task ID
    task_id = str(uuid.uuid4())
    async_function = is_async_function(func)

    if async_function:
        # Add asynchronous task
        task_scheduler.add_task(async_function, function_type, timeout_processing, task_name, task_id, func, *args,
                                **kwargs)

    if not async_function:
        # Add linear task
        task_scheduler.add_task(async_function, function_type, timeout_processing, task_name, task_id, func, *args,
                                **kwargs)

    return task_id
