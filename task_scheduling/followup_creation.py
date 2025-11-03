# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import threading
import time

from typing import Callable

from .common import logger
from .scheduler import get_result_api
from .task_creation import task_creation


def trigger_task_condition(main_task_type: str, main_task_id: str, dependent_task: Callable, *args) -> None:
    threading.Thread(target=wait_main_task_result, args=(main_task_type, main_task_id, dependent_task, args),
                     daemon=True).start()


def wait_main_task_result(main_task_type: str, main_task_id: str, dependent_task: Callable, args) -> None:
    while True:
        time.sleep(1.0)
        result = get_result_api(main_task_type, main_task_id, )
        if not result is None:
            # Ensure the result is a tuple
            if not isinstance(result, tuple):
                logger.error("Task result is not a tuple!")
                return None
            # Exit the loop if there is no problem
            break
    args += result
    task_creation(args[0], args[1], args[2], args[3], args[4], dependent_task, *args[5:])
    return None
