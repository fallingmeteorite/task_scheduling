# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import threading

from functools import wraps
from typing import Dict, Any

from .utils import wait_branch_thread_ended, branch_thread_control


# Decorator
def decorator_func(func, share_info, sharedtaskdict, timeout_processing, task_name):
    """
    Decorator function to wrap task functions with thread control.

    Args:
        func: The function to decorate
        share_info: Shared information for thread control
        sharedtaskdict: Shared dictionary for task data
        timeout_processing: Whether to enable timeout processing
        task_name: Name of the task

    Returns:
        Decorated function
    """

    @wraps(func)
    @branch_thread_control(share_info, sharedtaskdict, timeout_processing, task_name)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return result

    return wrapper


# Can only pass variable positional arguments
@wait_branch_thread_ended
def task_group(share_info: Any, sharedtaskdict: Any, task_signal_transmission: Any,
               task_dict: Dict) -> None:
    """
    Execute a group of tasks concurrently in separate threads.

    Args:
        share_info: Shared information for thread control
        sharedtaskdict: Shared dictionary for task data
        task_signal_transmission: Task signal transmission object
        task_dict: Dictionary mapping task names to their arguments
                   Format: {task_name: (function, timeout_processing, *args)}
    """
    threads = []
    # Create and start a thread
    for task_name, args in task_dict.items():
        thread = threading.Thread(
            target=decorator_func(args[0], share_info, sharedtaskdict, args[1], task_name),
            args=args[2:], daemon=True)
        threads.append(thread)
        thread.start()
