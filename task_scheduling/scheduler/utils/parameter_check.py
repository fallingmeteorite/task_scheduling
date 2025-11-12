# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Function inspection utilities.

This module provides utility functions for inspecting function parameters
and decorator metadata.
"""
import inspect

from typing import Callable


def get_param_count(func: Callable, *args, **kwargs) -> bool:
    """

    Args:
        func: function

    Returns: Are the parameters consistent?

    """
    return not len(inspect.signature(func).parameters) == len(args) + len(kwargs)


def retry_on_error_decorator_check(func: Callable) -> bool:
    """

    Args:
        func: function

    Returns: Add retry decorator?

    """
    return (hasattr(func, '_decorated_by') and
            getattr(func, '_decorated_by') == 'retry_on_error_decorator')
