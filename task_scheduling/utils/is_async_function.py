# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import inspect
from typing import Callable


def is_async_function(func: Callable) -> bool:
    """
    Determine if a function is an asynchronous function.

    Args:
        func (Callable): The function to check.

    Returns:
        bool: True if the function is asynchronous; otherwise, False.
    """
    return inspect.iscoroutinefunction(func)
