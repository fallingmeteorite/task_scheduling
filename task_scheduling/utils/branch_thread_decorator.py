# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import time
import uuid
from functools import wraps
from typing import Any, Callable

from ..common import logger
from ..config import config


def branch_thread_control(share_info: Any, _sharedtaskdict: Any, timeout_processing: bool, task_name: str) -> Any:
    """
        Control part of the running function.

        Args:
            task_manager (Any): Thread manager, used for a series of operations such as stopping and pausing.
            _threadterminator (Any): Terminate instance.
            StopException (Any): Error handling.
            timeout_processing (bool): Enable timeout handling.
            task_status_queue (queue.Queue): State transfer queue.
            task_name (str): task name.
        """
    task_manager, _threadterminator, StopException, ThreadingTimeout, TimeoutException, _threadsuspender, task_status_queue = share_info

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Assign a unique identification code
            task_id = str(uuid.uuid4())
            _sharedtaskdict.write(task_name, task_id)
            task_status_queue.put(("running", task_id, task_name, time.time(), None, None, timeout_processing))
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


def wait_branch_thread_ended(func: Callable) -> Any:
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get Task Manager
        task_manager = args[0][0]
        result = func(*args, **kwargs)
        task_manager.wait()
        return result

    return wrapper
