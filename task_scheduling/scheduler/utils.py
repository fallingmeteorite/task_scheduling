import threading
import time
from typing import Callable, Any


def is_async_function(func: Callable) -> bool:
    """
    Determine if a function is an asynchronous function.

    :param func: The function to check

    :return: True if the function is asynchronous; otherwise, False.
    """
    return inspect.iscoroutinefunction(func)


def interruptible_sleep(seconds: float or int) -> None:
    # Create an event object
    event = threading.Event()

    # Define a function that sets the event after a specified number of seconds
    def set_event():
        time.sleep(seconds)
        event.set()

    # Start a thread to execute set_event functions
    thread = threading.Thread(target=set_event, daemon=True)
    thread.start()

    # The main thread waits for the event to be set
    while not event.is_set():
        event.wait(0.01)

    thread.join(timeout=0)


import inspect


class AwaitDetector:
    def __init__(self):
        # Used to store the has_awaited status for different task_names
        self.task_status = {}

    # Used to detect the 'await' keyword in the code at runtime
    async def run_with_detection(self, task_name: str, func: Callable, *args, **kwargs) -> Any:
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

        if result is None:
            return None
        return result

    # Get the status of the specified task_name
    def get_task_status(self, task_name: str) -> bool or None:
        return self.task_status.get(task_name, None)

"""
import asyncio
async def test_func():
    await asyncio.sleep(1)
    return "Done"

asyncio.run(detector.run_with_detection("test", test_func))
print(detector.get_task_status("test"))  
# Output: True or False, depending on whether 'await' is used in test_func
"""
