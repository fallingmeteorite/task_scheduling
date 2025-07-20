# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import uuid
from typing import Callable

from .common.log_config import logger
from .scheduler import io_asyncio_task, io_liner_task, cpu_liner_task, cpu_asyncio_task, timer_task
from .scheduler_management import TaskScheduler
from .utils import is_async_function

task_scheduler = TaskScheduler()


def task_creation(delay: int or None, daily_time: str or None, function_type: str, timeout_processing: bool,
                  task_name: str,
                  func: Callable,
                  *args, **kwargs) -> str or None:
    """
    Add a task to the queue, choosing between asynchronous or linear task based on the function type.
    Generate a unique task ID and return it.

    :param delay:Countdown time.
    :param daily_time:The time it will run.
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

    if async_function and not function_type == "timer":
        # Add asynchronous task
        task_scheduler.add_task(None, None, async_function, function_type, timeout_processing, task_name, task_id, func,
                                *args,
                                **kwargs)

    if not async_function and not function_type == "timer":
        # Add linear task
        task_scheduler.add_task(None, None, async_function, function_type, timeout_processing, task_name, task_id, func,
                                *args,
                                **kwargs)

    if function_type == "timer":
        # Add timer task
        task_scheduler.add_task(delay, daily_time, async_function, function_type, timeout_processing, task_name,
                                task_id, func,
                                *args,
                                **kwargs)

    return task_id


def shutdown(force_cleanup: bool) -> None:
    """
        :param force_cleanup: Force the end of a running task

        Shutdown the scheduler, stop all tasks, and release resources.
        Only checks if the scheduler is running and forces a shutdown if necessary.
        """

    logger.info("Starting shutdown TaskScheduler.")
    task_scheduler.shutdown()

    # Shutdown scheduler if running
    if hasattr(timer_task, "_scheduler_started") and timer_task._scheduler_started:
        logger.info("Detected Timer task scheduler is running, shutting down...")
        timer_task.stop_scheduler(force_cleanup)

    # Shutdown scheduler if running
    if hasattr(cpu_asyncio_task, "_scheduler_started") and cpu_asyncio_task._scheduler_started:
        logger.info("Detected Cpu asyncio task scheduler is running, shutting down...")
        cpu_asyncio_task.stop_scheduler(force_cleanup)

    # Shutdown scheduler if running
    if hasattr(cpu_liner_task, "_scheduler_started") and cpu_liner_task._scheduler_started:
        logger.info("Detected Cpu linear task scheduler is running, shutting down...")
        cpu_liner_task.stop_scheduler(force_cleanup)

    # Shutdown scheduler if running
    if hasattr(io_asyncio_task, "_scheduler_started") and io_asyncio_task._scheduler_started:
        logger.info("Detected io asyncio task scheduler is running, shutting down...")
        io_asyncio_task.stop_all_schedulers(force_cleanup)

    # Shutdown scheduler if running
    if hasattr(io_liner_task, "_scheduler_started") and io_liner_task._scheduler_started:
        logger.info("Detected io linear task scheduler is running, shutting down...")
        io_liner_task.stop_scheduler(force_cleanup)

    logger.info("All scheduler has been shut down.")
