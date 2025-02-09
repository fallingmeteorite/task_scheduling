# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import inspect
import json
import os
import threading
import time
from typing import Callable, Any, Optional

from ..common import logger


def is_async_function(func: Callable) -> bool:
    """
    Determine if a function is an asynchronous function.

    Args:
        func (Callable): The function to check.

    Returns:
        bool: True if the function is asynchronous; otherwise, False.
    """
    return inspect.iscoroutinefunction(func)


def interruptible_sleep(seconds: float or int) -> None:
    """
    Sleep for a specified number of seconds, but can be interrupted by setting an event.

    Args:
        seconds (float or int): Number of seconds to sleep.
    """
    event = threading.Event()

    def set_event():
        time.sleep(seconds)
        event.set()

    thread = threading.Thread(target=set_event, daemon=True)
    thread.start()

    while not event.is_set():
        event.wait(0.01)

    thread.join(timeout=0)


class AwaitDetector:
    def __init__(self):
        """
        Initialize the AwaitDetector class to keep track of whether tasks use the 'await' keyword.
        """
        # Used to store the has_awaited status for different task_names
        self.task_status = {}

    # Used to detect the 'await' keyword in the code at runtime
    async def run_with_detection(self,
                                 task_name: str,
                                 func: Callable,
                                 *args, **kwargs) -> Any:
        """
        Run a task and detect if it uses the 'await' keyword.

        Args:
            task_name (str): The name of the task.
            func (Callable): The function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            Any: Result of the task execution.
        """
        # Initialize the status for the current task_name
        self.task_status[task_name] = False

        # Check if the function is a coroutine function
        if not inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)

        # Check if the 'await' keyword is contained in the function body
        try:
            source = inspect.getsource(func)
            if "await" in source:
                self.task_status[task_name] = True
        except (OSError, TypeError):
            # If the source code cannot be obtained (e.g., built-in functions), skip static checking
            pass

        # Run the function
        result = await func(*args, **kwargs)

        # Reset the status for the current task_name
        self.task_status[task_name] = False

        return result

    def get_task_status(self,
                        task_name: str) -> bool or None:
        """
        Get the status of the specified task_name.

        Args:
            task_name (str): The name of the task.

        Returns:
            bool or None: True if the task used 'await', False if it did not, and None if the task_name is not found.
        """
        return self.task_status.get(task_name, None)


def get_package_directory() -> str:
    """
    Get the path of the directory containing the __init__.py file.

    Returns:
        str: Path of the package directory.
    """
    return os.path.dirname(os.path.abspath(__file__))



"""
# Example usage of AwaitDetector
detector = AwaitDetector()

async def test_func():
    await asyncio.sleep(1)
    return "Done"

asyncio.run(detector.run_with_detection("test", test_func))
print(detector.get_task_status("test"))  # Output: True or False, depending on whether 'await' is used in test_func
"""
