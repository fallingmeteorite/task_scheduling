import inspect
import atexit
from typing import Callable

from .scheduler.asyn_task_assignment import asyntask
from .scheduler.line_task_assignment import linetask
from .common.logging import logger


def is_async_function(func: Callable) -> bool:
    """
    Determine if a function is an asynchronous function.

    :param func: The function to check.
    :return: True if the function is asynchronous; otherwise, False.
    """
    return inspect.iscoroutinefunction(func)


def add_task(timeout_processing: bool, task_id: str, func: Callable, *args, **kwargs) -> None:
    """
    Add a task to the queue, choosing between asynchronous or linear tasks based on the function type.

    :param timeout_processing: Whether to enable timeout processing.
    :param task_id: Task ID.
    :param func: Task function.
    :param args: Positional arguments for the task function.
    :param kwargs: Keyword arguments for the task function.
    """
    if is_async_function(func):
        # Run asynchronous task
        asyntask.add_task(timeout_processing, task_id, func, *args, **kwargs)
    else:
        # Run linear task
        linetask.add_task(timeout_processing, task_id, func, *args, **kwargs)

    # Explicitly delete no longer used variables (optional)
    del timeout_processing
    del task_id
    del func
    del args
    del kwargs


def shutdown() -> None:
    """
    Shutdown the scheduler, stop all tasks, and release resources.
    """
    # Check if the asynchronous task scheduler has started
    if asyntask.scheduler_started:
        logger.info("Detected asynchronous task scheduler is running, shutting down...")
        asyntask.stop_scheduler()

    # Check if the linear task scheduler has started
    if linetask.scheduler_started:
        logger.info("Detected linear task scheduler is running, shutting down...")
        linetask.stop_scheduler()

    logger.info("All schedulers have been shut down, resources have been released.")

# Register the opt-out function
atexit.register(shutdown)
