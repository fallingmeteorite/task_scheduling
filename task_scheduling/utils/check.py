# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Function type inspection utilities.

This module provides functions to detect asynchronous functions
and check for specific decorator markers.
"""

import inspect

from typing import Callable


SUPPORTED_FUNCTION_TYPES = ("io", "cpu", "timer")


def is_async_function(func: Callable) -> bool:
    """
    Determine if a function is an asynchronous function.

    Args:
        func: The function to check.

    Returns:
        True if the function is asynchronous, otherwise False.
    """
    return inspect.iscoroutinefunction(func)


def is_valid_function_type(function_type: str) -> bool:
    """
    Check whether the provided function type is supported by the scheduler.

    Args:
        function_type: Function type string to validate.

    Returns:
        True if the function type is one of the supported scheduler types.
    """
    return function_type in SUPPORTED_FUNCTION_TYPES


def wait_branch_thread_ended_check(func: Callable) -> bool:
    """
    Check if a function has been decorated with wait_branch_thread_ended.

    Args:
        func: The function to check.

    Returns:
        True if the function has the wait_branch_thread_ended decorator, otherwise False.
    """
    return (
            hasattr(func, '_decorated_by')
            and getattr(func, '_decorated_by') == 'wait_branch_thread_ended'
    )
