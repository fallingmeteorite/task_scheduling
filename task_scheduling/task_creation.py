# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Task creation and management utilities.

This module provides functions for creating and managing different types of tasks
including asynchronous, linear, and timer-based tasks with proper type handling.
"""
import uuid
import inspect

from typing import Callable, Union

from .manager import task_scheduler
from .common import logger


def wait_branch_thread_ended_check(func: Callable) -> bool:
    """

    Args:
        func: function

    Returns: Add retry decorator?

    """
    return (hasattr(func, '_decorated_by') and
            getattr(func, '_decorated_by') == 'wait_branch_thread_ended')


def is_async_function(func: Callable) -> bool:
    """
    Determine if a function is an asynchronous function.

    Args:
        func (Callable): The function to check.

    Returns:
        bool: True if the function is asynchronous; otherwise, False.
    """
    return inspect.iscoroutinefunction(func)


def task_creation(delay: Union[int, None], daily_time: Union[str, None], function_type: str, timeout_processing: bool,
                  task_name: str,
                  func: Callable,
                  priority: str,
                  *args, **kwargs) -> Union[str, None]:
    """
    Add a task to the queue, choosing between asynchronous or linear task based on the function type.
    Generate a unique task ID and return it.

    :param delay:Countdown time.
    :param daily_time:The time it will run.
    :param function_type:The type of the function.
    :param timeout_processing: Whether to enable timeout processing.
    :param task_name: The task name.
    :param func: The task function.
    :param priority: Mission importance level.
    :param args: Positional arguments for the task function.
    :param kwargs: Keyword arguments for the task function.
    :return: A unique task ID.
    """
    # Generate a unique task ID
    task_id = str(uuid.uuid4())
    async_function = is_async_function(func)
    if wait_branch_thread_ended_check(func):
        if not function_type == "cpu":
            logger.error("Experimental tasks must specify the function type as FUNCTION_TYPE_CPU!")
            return False

    if async_function and not function_type == "timer":
        # Add asynchronous task
        task_scheduler.add_task(None, None, async_function, function_type, timeout_processing, task_name, task_id, func,
                                priority,
                                *args,
                                **kwargs)

    if not async_function and not function_type == "timer":
        # Add linear task
        task_scheduler.add_task(None, None, async_function, function_type, timeout_processing, task_name, task_id, func,
                                priority,
                                *args,
                                **kwargs)

    if function_type == "timer":
        # Add timer task
        task_scheduler.add_task(delay, daily_time, async_function, function_type, timeout_processing, task_name,
                                task_id, func, priority,
                                *args,
                                **kwargs)

    return task_id
