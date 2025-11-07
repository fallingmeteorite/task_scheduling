# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import inspect

from typing import Callable


def get_param_count(func: Callable, *args, **kwargs) -> bool:
    """

    Args:
        func: function

    Returns: Are the parameters consistent?

    """
    return not len(inspect.signature(func).parameters) == len(args) + len(kwargs)
