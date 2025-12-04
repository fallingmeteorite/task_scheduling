# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Retry decorator for handling task failures with exponential backoff.

This module provides a decorator for automatically retrying functions when
specific exceptions occur, with configurable retry attempts and delays.
"""


def retry_on_error(
        exceptions,
        max_attempts,
        delay):
    """
    Decorator for retrying tasks when specific exceptions occur.

    Args:
        exceptions: Exception types to retry. If None, retry on all exceptions.
        max_attempts: Maximum number of retry attempts (default: 3).
        delay: Initial delay in seconds between retries (default: 1).

    Returns:
        A decorator that wraps the function with retry logic.
    """
    import functools
    import time
    from typing import Callable, Any

    if exceptions is None:
        exceptions = Exception

    def decorator(func: Callable) -> Callable:
        """Inner decorator function that applies retry logic to the target function.

        Args:
            func: The target function to wrap with retry logic.

        Returns:
            Wrapped function with retry capabilities.
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            """Wrapper function that implements the retry logic.

            Args:
                *args: Positional arguments passed to the target function.
                **kwargs: Keyword arguments passed to the target function.

            Returns:
                The result of the target function if successful.

            Raises:
                Exception: The last exception encountered if all retries fail.
            """
            current_delay = delay
            attempt = 0
            while True:
                try:
                    return func(*args[1:], **kwargs)
                except exceptions as error:
                    if attempt == max_attempts:
                        raise error

                    attempt += 1
                    time.sleep(current_delay)
                    # Optional: Implement exponential backoff
                except Exception as error:
                    # Caught an exception that is not in the retry list
                    raise error

        # Mark the function as decorated for identification
        wrapper._decorated_by = 'retry_on_error_decorator'
        return wrapper

    return decorator
