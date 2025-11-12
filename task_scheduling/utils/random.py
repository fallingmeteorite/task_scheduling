# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import uuid


def random_name(prefix: str) -> str:
    """
    Generate a random name with the specified prefix.

    Args:
        prefix: The prefix to use for the random name

    Returns:
        A random name combining the prefix and a UUID
    """
    return f"{prefix}{str(uuid.uuid4())}"
