import time
import functools
from typing import Union, Type, Tuple, Callable, Any

from ..common import logger


def retry_on_error(
        exceptions: Union[Type[Exception], Tuple[Type[Exception], ...], None],
        max_attempts: int,
        delay: Union[float, int]) -> Any:
    """
    Task retry decorator

    Args:
        exceptions: Exception types to retry (None for all exceptions)
        max_attempts: Maximum retry attempts
        delay: Initial delay in seconds
    """
    if exceptions is None:
        exceptions = Exception

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args[1:], **kwargs)
                except exceptions as error:
                    if attempt == max_attempts:
                        raise error

                    logger.warning(f"Task |{args[0]}| encountered a specific error, starting to retry the task")
                    time.sleep(current_delay)
                except Exception as error:
                    # Caught an exception that is not in the retry list
                    logger.error(f"Unhandled error type: {type(e).__name__}, message: {error}")
                    raise error

        wrapper._decorated_by = 'retry_on_error_decorator'
        return wrapper

    return decorator
