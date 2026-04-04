# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Task management API module.

This module provides a unified API for managing different types of tasks
(IO-bound, CPU-bound, timer) with support for asynchronous and linear execution modes.
"""
import time
import threading
from typing import Any, Union, Callable

from task_scheduling.common import logger, config
from task_scheduling.scheduler.cpu_asyncio_task import cpu_asyncio_task, shared_status_info_asyncio
from task_scheduling.scheduler.cpu_liner_task import cpu_liner_task, shared_status_info_liner
from task_scheduling.scheduler.io_asyncio_task import io_asyncio_task
from task_scheduling.scheduler.io_liner_task import io_liner_task
from task_scheduling.scheduler.timer_task import timer_task

# Define mapping from task types to processors
_TASK_HANDLERS = {
    "io_asyncio_task": io_asyncio_task,
    "io_liner_task": io_liner_task,
    "cpu_liner_task": cpu_liner_task,
    "cpu_asyncio_task": cpu_asyncio_task,
    "timer_task": timer_task,
}

_cleanup_thread = None
_cleanup_thread_lock = threading.Lock()


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


def _cleanup_task_results(handler: Any,
                          current_time: Union[float, None] = None,
                          max_result_count: Union[int, None] = None,
                          max_result_age: Union[int, None] = None) -> None:
    """
    Remove expired task results in place for a single handler.

    Args:
        handler: Scheduler handler containing `_task_results` and `_lock`.
        current_time: Timestamp used for age comparison.
        max_result_count: Threshold that enables cleanup.
        max_result_age: Maximum retained result age in seconds.
    """
    if current_time is None:
        current_time = time.time()
    if max_result_count is None:
        max_result_count = config["maximum_result_storage"]
    if max_result_age is None:
        max_result_age = config["maximum_result_time_storage"]

    with handler._lock:
        if len(handler._task_results) < max_result_count:
            return

        expired_task_ids = [
            task_id for task_id, value in handler._task_results.items()
            if int(current_time - value[1]) >= max_result_age
        ]
        for task_id in expired_task_ids:
            handler._task_results.pop(task_id, None)


def ensure_cleanup_results_thread_started() -> None:
    """
    Start the cleanup thread once for the current process.
    """
    global _cleanup_thread

    with _cleanup_thread_lock:
        if _cleanup_thread is not None and _cleanup_thread.is_alive():
            return

        _cleanup_thread = threading.Thread(target=cleanup_results_api, daemon=True)
        _cleanup_thread.start()


def cleanup_results_api() -> None:
    """
    Clear useless return results.
    """
    while True:
        for handler in _TASK_HANDLERS.values():
            _cleanup_task_results(handler)
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
