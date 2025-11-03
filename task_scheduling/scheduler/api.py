# -*- coding: utf-8 -*-
# Author: fallingmeteorite
from typing import Any

from ..common import logger
from .timer_task import timer_task
from .io_asyncio_task import io_asyncio_task
from .io_liner_task import io_liner_task
from .cpu_asyncio_task import cpu_asyncio_task
from .cpu_liner_task import cpu_liner_task
from .utils import shared_task_info


def kill_api(task_type: str, task_id: str) -> bool:
    """

    Args:
        task_type: Task Type
        task_id: Task ID
    """
    if task_type == "io_asyncio_task":
        return io_asyncio_task.force_stop_task(task_id)
    if task_type == "io_liner_task":
        return io_liner_task.force_stop_task(task_id)
    if task_type == "cpu_liner_task":
        return cpu_liner_task.force_stop_task(task_id)
    if task_type == "cpu_asyncio_task":
        return cpu_asyncio_task.force_stop_task(task_id)
    if task_type == "timer_task":
        return timer_task.force_stop_task(task_id)
    return False


def pause_api(task_type: str, task_id: str) -> bool:
    """

    Args:
        task_type: Task Type
        task_id: Task ID
    """
    if task_type == "io_asyncio_task":
        return io_asyncio_task.pause_task(task_id)
    if task_type == "io_liner_task":
        return io_liner_task.pause_task(task_id)
    if task_type == "cpu_liner_task":
        return cpu_liner_task.pause_task(task_id)
    if task_type == "cpu_asyncio_task":
        return cpu_asyncio_task.pause_task(task_id)
    if task_type == "timer_task":
        return timer_task.pause_task(task_id)
    return False


def resume_api(task_type: str, task_id: str) -> bool:
    """

    Args:
        task_type: Task Type
        task_id: Task ID
    """
    if task_type == "io_asyncio_task":
        return io_asyncio_task.resume_task(task_id)
    if task_type == "io_liner_task":
        return io_liner_task.resume_task(task_id)
    if task_type == "cpu_liner_task":
        return cpu_liner_task.resume_task(task_id)
    if task_type == "cpu_asyncio_task":
        return cpu_asyncio_task.resume_task(task_id)
    if task_type == "timer_task":
        return timer_task.resume_task(task_id)
    return False


def get_result_api(task_type: str, task_id: str) -> Any:
    """

    Args:
        task_type: Task Type
        task_id: Task ID
    """
    if task_type == "io_asyncio_task":
        return io_asyncio_task.get_task_result(task_id)
    if task_type == "io_liner_task":
        return io_liner_task.get_task_result(task_id)
    if task_type == "cpu_liner_task":
        return cpu_liner_task.get_task_result(task_id)
    if task_type == "cpu_asyncio_task":
        return cpu_asyncio_task.get_task_result(task_id)
    if task_type == "timer_task":
        return timer_task.get_task_result(task_id)

    return None


def shutdown_api(force_cleanup: bool) -> None:
    # Shutdown scheduler if running
    if hasattr(timer_task, "_scheduler_started") and timer_task._scheduler_started:
        logger.info("Detected Timer task scheduler is running, shutting down...")
        timer_task.stop_scheduler(force_cleanup)

    # Shutdown scheduler if running
    if hasattr(io_asyncio_task, "_scheduler_started") and io_asyncio_task._scheduler_started:
        logger.info("Detected io asyncio task scheduler is running, shutting down...")
        io_asyncio_task.stop_all_schedulers(force_cleanup)

    # Shutdown scheduler if running
    if hasattr(io_liner_task, "_scheduler_started") and io_liner_task._scheduler_started:
        logger.info("Detected io linear task scheduler is running, shutting down...")
        io_liner_task.stop_scheduler(force_cleanup)

    # Shutdown scheduler if running
    if hasattr(cpu_asyncio_task, "_scheduler_started") and cpu_asyncio_task._scheduler_started:
        logger.info("Detected Cpu asyncio task scheduler is running, shutting down...")
        cpu_asyncio_task.stop_scheduler(force_cleanup)

    # Shutdown scheduler if running
    if hasattr(cpu_liner_task, "_scheduler_started") and cpu_liner_task._scheduler_started:
        logger.info("Detected Cpu linear task scheduler is running, shutting down...")
        cpu_liner_task.stop_scheduler(force_cleanup)

    # Close the shared information channel
    shared_task_info.manager.shutdown()
