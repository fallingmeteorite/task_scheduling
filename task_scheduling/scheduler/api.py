# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Task management API module.

This module provides a unified API for managing different types of tasks
(IO-bound, CPU-bound, timer) with support for asynchronous and linear execution modes.
"""
import time

from typing import Any, Union, Callable

from .cpu_asyncio_task import cpu_asyncio_task, shared_status_info_asyncio
from .cpu_liner_task import cpu_liner_task, shared_status_info_liner
from .io_asyncio_task import io_asyncio_task
from .io_liner_task import io_liner_task
from .timer_task import timer_task
from ..common import logger, config

# Define mapping from task types to processors
_TASK_HANDLERS = {
    "io_asyncio_task": io_asyncio_task,
    "io_liner_task": io_liner_task,
    "cpu_liner_task": cpu_liner_task,
    "cpu_asyncio_task": cpu_asyncio_task,
    "timer_task": timer_task,
}


def _get_handler(task_type: str):
    """Get Task Processor"""
    return _TASK_HANDLERS.get(task_type)


def add_api(task_type: str, delay: Union[int, None], daily_time: Union[str, None], timeout_processing: bool,
            task_name: str, task_id: str, func: Callable, priority: str,
            *args, **kwargs) -> Union[str, None]:
    """
    Add a task to the appropriate scheduler based on task type.

    Args:
        task_type: Type of task ("io_asyncio_task", "io_liner_task", "cpu_liner_task", "cpu_asyncio_task", "timer_task")
        delay: Countdown time for timer tasks
        daily_time: The time it will run for timer tasks
        timeout_processing: Whether to enable timeout processing
        task_name: The task name
        task_id: The task ID
        func: The task function
        priority: Mission importance level
        args: Positional arguments for the task function
        kwargs: Keyword arguments for the task function

    Returns:
        Task state or None if task type is invalid
    """
    handler = _get_handler(task_type)
    if not handler:
        logger.error("The specified scheduler could not be found!")
        return "The specified scheduler could not be found!"

    # Adjust parameter passing according to the task type
    if task_type == "timer_task":
        return handler.add_task(delay, daily_time, timeout_processing, task_name, task_id, func, *args, **kwargs)
    elif task_type in ("io_liner_task", "cpu_liner_task"):
        return handler.add_task(timeout_processing, task_name, task_id, func, priority, *args, **kwargs)
    else:
        return handler.add_task(timeout_processing, task_name, task_id, func, *args, **kwargs)


def kill_api(task_type: str, task_id: str) -> bool:
    """
    Force stop a task.

    Args:
        task_type: Task Type
        task_id: Task ID

    Returns:
        True if task was stopped successfully, False otherwise
    """
    handler = _get_handler(task_type)
    return handler.force_stop_task(task_id)


def pause_api(task_type: str, task_id: str) -> bool:
    """
    Pause a task.

    Args:
        task_type: Task Type
        task_id: Task ID

    Returns:
        True if task was paused successfully, False otherwise
    """
    handler = _get_handler(task_type)
    return handler.pause_task(task_id)


def resume_api(task_type: str, task_id: str) -> bool:
    """
    Resume a paused task.

    Args:
        task_type: Task Type
        task_id: Task ID

    Returns:
        True if task was resumed successfully, False otherwise
    """
    handler = _get_handler(task_type)
    return handler.resume_task(task_id)


def get_result_api(task_type: str, task_id: str) -> Any:
    """
    Get the result of a task.

    Args:
        task_type: Task Type
        task_id: Task ID

    Returns:
        Task result or None if not available
    """
    handler = _get_handler(task_type)
    return handler.get_task_result(task_id)


def cleanup_results_api() -> None:
    """
    Clear useless return results.
    """
    max_result_count = config["maximum_result_storage"]
    while True:
        for handler in _TASK_HANDLERS.values():
            del_task_results = []
            # Check if the cleaning limit has been reached
            if len(handler._task_results) >= max_result_count:
                # Lock
                with handler._lock:
                    cache_task_results = handler._task_results.copy()
                # Delete results that have been inactive for too long
                for key, value in cache_task_results.items():
                    if int(time.time() - value[1]) >= config["maximum_result_time_storage"]:
                        del_task_results.append(key)
                # Delete the data for 'drinking' in the dictionary
                for task_id in del_task_results:
                    del cache_task_results[task_id]
                # Lock
                with handler._lock:
                    handler._task_results = cache_task_results
        try:
            time.sleep(2.0)
        except KeyboardInterrupt:
            pass


def shutdown_api() -> None:
    """
    Shutdown all task schedulers and clean up resources.
    """
    # Define the list of schedulers to be shut down
    schedulers = [
        (timer_task, "Timer task", "_scheduler_started"),
        (io_asyncio_task, "io asyncio task", "_scheduler_started"),
        (io_liner_task, "io linear task", "_scheduler_started"),
        (cpu_asyncio_task, "Cpu asyncio task", "_scheduler_started"),
        (cpu_liner_task, "Cpu linear task", "_scheduler_started"),
    ]

    for scheduler, name, attr_name in schedulers:
        if getattr(scheduler, attr_name, False):
            logger.debug(f"Detected {name} scheduler is running, shutting down...")
            # Call the corresponding shutdown method according to the different schedulers
            if hasattr(scheduler, 'stop_all_schedulers'):
                scheduler.stop_all_schedulers()
            elif hasattr(scheduler, 'stop_scheduler'):
                scheduler.stop_scheduler()

    # Close the shared channel
    shared_status_info_asyncio.channel_shutdown()
    shared_status_info_liner.channel_shutdown()
