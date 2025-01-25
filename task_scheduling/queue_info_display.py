# -*- coding: utf-8 -*-
import time
from typing import Dict

from .scheduler.asyn_task_assignment import asyntask
from .scheduler.line_task_assignment import linetask


def format_task_info(task_id: str, details: Dict) -> str:
    """
    Format task information.

    :param task_id: Task ID.
    :param details: Task details.
    :return: Formatted task information.
    """
    task_name = details.get("task_name", "Unknown")  # Get task name, default to "Unknown" if not provided
    start_time = details.get("start_time", 0)
    end_time = details.get("end_time", 0)
    status = details.get("status", "unknown")

    # Calculate elapsed time
    if status == "running":
        elapsed_time = time.time() - start_time if time.time() - start_time >= 0 else 0
        elapsed_time_display = f"{elapsed_time:.2f}"

    elif end_time == "NaN":
        elapsed_time_display = "NaN"

    else:
        elapsed_time_display = "NaN"

    # Add special hints based on status
    status_hint = ""
    if status == "timeout":
        status_hint = " (Task timed out)"
    elif status == "failed":
        status_hint = " (Task failed)"
    elif status == "cancelled":
        status_hint = " (Task cancelled)"
    # Format task information with task_name and task_id
    return f"Name: {task_name}, ID: {task_id}, Process Status: {status}{status_hint}, Elapsed Time: {elapsed_time_display} seconds\n"


def get_queue_info_string(task_queue, queue_type: str) -> str:
    """
    Get the string of queue information.

    :param task_queue: Task queue object.
    :param queue_type: Queue type (e.g., "line" or "asyncio").
    :return: String of queue information.
    """
    try:
        queue_info = task_queue.get_queue_info()
        info = (
            f"\n{queue_type} queue size: {queue_info['queue_size']}, "
            f"Running tasks count: {queue_info['running_tasks_count']}\n"
        )

        # Output task details
        for task_id, details in queue_info['task_details'].items():
            if not "pending" == details["status"]:
                info += format_task_info(task_id, details)

        if queue_info.get("error_logs"):
            info += f"\n{queue_type} error logs:\n"
            for error in queue_info["error_logs"]:
                info += (
                    f"Task ID: {error['task_id']}, Error time: {error['error_time']}, "
                    f"Error message: {error['error_message']}\n"
                )

        return info

    except Exception as e:
        return f"Error occurred while getting {queue_type} queue information: {e}\n"


def get_all_queue_info(queue_type: str) -> str:
    """
    Get the string of all queue information.

    :param queue_type: Queue type (e.g., "line" or "asyncio").
    :return: String of all queue information.
    """
    if queue_type == "line":
        return get_queue_info_string(linetask, queue_type="line")
    elif queue_type == "asyncio":
        return get_queue_info_string(asyntask, queue_type="asyncio")
    else:
        return f"Unknown queue type: {queue_type}"
