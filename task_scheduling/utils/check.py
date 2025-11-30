# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Function type inspection utilities.

This module provides functions to detect asynchronous functions
and check for specific decorator markers.
"""

import inspect

from typing import Callable


def is_async_function(func: Callable) -> bool:
    """
    Determine if a function is an asynchronous function.

    Args:
        func: The function to check.

    Returns:
        True if the function is asynchronous, otherwise False.
    """
    return inspect.iscoroutinefunction(func)


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