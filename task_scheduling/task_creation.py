# -*- coding: utf-8 -*-
import uuid
from typing import Callable

from .common.log_config import logger
from .scheduler import io_async_task, io_liner_task, cpu_liner_task, cpu_async_task, timer_task
from .scheduler.utils import is_async_function
from .scheduler_management import TaskScheduler

task_scheduler = TaskScheduler()


def task_creation(delay: int or None, daily_time: str or None, function_type: str, timeout_processing: bool,
                  task_name: str,
                  func: Callable, *args,
                  **kwargs) -> str or None:
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

    if async_function:
        # Add asynchronous task
        task_scheduler.add_task(None, None, async_function, function_type, timeout_processing, task_name, task_id, func,
                                *args,
                                **kwargs)

    if not async_function:
        # Add linear task
        task_scheduler.add_task(None, None, async_function, function_type, timeout_processing, task_name, task_id, func,
                                *args,
                                **kwargs)

    if function_type == "time":
        # Add timer task
        task_scheduler.add_task(delay, daily_time, None, function_type, timeout_processing, task_name, task_id, func,
                                *args,
                                **kwargs)

    return task_id


def shutdown(force_cleanup: bool) -> None:
    """
        :param force_cleanup: Force the end of a running task

        Shutdown the scheduler, stop all tasks, and release resources.
        Only checks if the scheduler is running and forces a shutdown if necessary.
        """

    task_scheduler.shutdown()

    # Shutdown asynchronous task scheduler if running
    if hasattr(timer_task, "scheduler_started") and timer_task.scheduler_started:
        logger.info("Detected Cpu linear task scheduler is running, shutting down...")
        timer_task.stop_scheduler(force_cleanup)
        logger.info("Cpu linear task scheduler has been shut down.")


    # Shutdown asynchronous task scheduler if running
    if hasattr(cpu_async_task, "scheduler_started") and cpu_async_task.scheduler_started:
        logger.info("Detected Cpu asyncio task scheduler is running, shutting down...")
        cpu_async_task.stop_scheduler(force_cleanup)
        logger.info("Cpu asyncio task scheduler has been shut down.")

    # Shutdown asynchronous task scheduler if running
    if hasattr(cpu_liner_task, "scheduler_started") and cpu_liner_task.scheduler_started:
        logger.info("Detected Cpu linear task scheduler is running, shutting down...")
        cpu_liner_task.stop_scheduler(force_cleanup)
        logger.info("Cpu linear task scheduler has been shut down.")


    # Shutdown asynchronous task scheduler if running
    if hasattr(io_async_task, "scheduler_started") and io_async_task.scheduler_started:
        logger.info("Detected io asyncio task scheduler is running, shutting down...")
        io_async_task.stop_all_schedulers(force_cleanup)
        logger.info("Io asyncio task scheduler has been shut down.")

    # Shutdown linear task scheduler if running
    if hasattr(io_liner_task, "scheduler_started") and io_liner_task.scheduler_started:
        logger.info("Detected io linear task scheduler is running, shutting down...")
        io_liner_task.stop_scheduler(force_cleanup)
        logger.info("Io linear task scheduler has been shut down.")



    logger.info("All scheduler has been shut down.")
