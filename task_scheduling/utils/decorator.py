# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Thread management utilities for branch thread control and synchronization.

This module provides decorators and functions for managing branch threads
with proper lifecycle control, timeout handling, and synchronization.
"""

import time
import uuid
import threading

from functools import wraps
from typing import Any, Callable

from ..common import logger, config


def wait_ended() -> None:
    """Wait for all branch threads to complete before main thread exits.

    Prevents errors caused by branch threads still running after the main thread ends
    by blocking until the thread count reaches an acceptable level.
    """
    # Prevent errors caused by branch threads still running after the main thread ends
    while True:
        if threading.active_count() <= 2:
            break
        time.sleep(0.01)


def branch_thread_control(share_info: Any, _sharedtaskdict: Any, timeout_processing: bool, task_name: str) -> Any:
    """Create a decorator for controlling branch thread execution with proper lifecycle management.

    Args:
        share_info: Tuple containing shared information for thread management
        _sharedtaskdict: Shared dictionary for task data storage
        timeout_processing: Boolean indicating if timeout handling is enabled
        task_name: Name of the task for identification

    Returns:
        A decorator function that wraps the target function with thread control
    """
    (task_group_name, task_manager, _threadterminator, StopException, ThreadingTimeout, TimeoutException,
     _threadsuspender, task_status_queue) = share_info

    def decorator(func: Callable) -> Callable:
        """Decorator function that adds thread control to the target function.

        Args:
            func: The target function to wrap with thread control

        Returns:
            Wrapped function with thread control capabilities
        """

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            """Wrapper function that implements thread control logic.

            Args:
                *args: Positional arguments passed to the target function
                **kwargs: Keyword arguments passed to the target function

            Returns:
                Result of the target function execution or error indicator
            """
            # Assign a unique identification code
            task_id = str(uuid.uuid4())
            _sharedtaskdict.write(task_name, task_id)
            task_status_queue.put(
                ("running", task_id, f"{task_group_name}|{task_name}", time.time(), None, None, timeout_processing))

            with _threadterminator.terminate_control() as terminate_ctx:
                with _threadsuspender.suspend_context() as pause_ctx:
                    try:
                        return_results = None
                        task_manager.add(terminate_ctx, pause_ctx, task_id)
                        if timeout_processing:
                            with ThreadingTimeout(seconds=config["watch_dog_time"], swallow_exc=False):
                                return func(*args, **kwargs)
                        else:
                            return func(*args, **kwargs)

                    except StopException:
                        logger.warning(f"task | {task_id} | cancelled, forced termination")
                        task_status_queue.put(("cancelled", task_id, None, None, time.time(), None, None))
                        return_results = "error happened"

                    except TimeoutException:
                        logger.warning(f"task | {task_id} | timed out, forced termination")
                        task_status_queue.put(("timeout", task_id, None, None, None, None, None))
                        return_results = "error happened"

                    except Exception as error:
                        # Whether to throw an exception
                        if config["exception_thrown"]:
                            raise

                        logger.error(f"task | {task_id} | execution failed: {error}")
                        task_status_queue.put(("failed", task_id, None, None, time.time(), None, error))
                        return_results = "error happened"

                    finally:
                        if return_results is None:
                            task_status_queue.put(("completed", task_id, None, None, time.time(), None, None))
                        task_manager.remove(task_id)

        return wrapper

    return decorator


def wait_branch_thread_ended(func: Callable) -> Callable:
    """Decorator to wait for branch threads to end before function returns.

    Args:
        func: Function to decorate that may spawn branch threads

    Returns:
        Decorated function that waits for branch threads before returning
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        """Wrapper function that waits for branch threads after execution.

        Args:
            *args: Positional arguments passed to the target function
            **kwargs: Keyword arguments passed to the target function

        Returns:
            Result of the target function execution
        """
        # Execute the original function
        result = func(*args, **kwargs)
        # Wait for all branch threads to complete
        wait_ended()
        return result

    # Mark the function as decorated for identification
    wrapper._decorated_by = 'wait_branch_thread_ended'

    return wrapper
