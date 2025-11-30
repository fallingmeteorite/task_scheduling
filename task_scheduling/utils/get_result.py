# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Task result retrieval module.

This module provides asynchronous functionality for retrieving task results
from a remote server using custom protocol over TCP sockets.
"""

import asyncio
import pickle

from task_scheduling.common import config


async def get_task_result(task_id: str, timeout: float = 30.0):
    """Get task result (asynchronous function)

    Args:
        task_id: Task ID
        timeout: Timeout in seconds

    Returns:
        Serialized result data, returns None if not found
    """
    request = {
        'action': 'get',
        'task_id': task_id,
        'timeout': timeout
    }

    reader, writer = await asyncio.open_connection('localhost', config["get_ip"])

    request_data = pickle.dumps(request)
    writer.write(len(request_data).to_bytes(4, 'big'))
    writer.write(request_data)
    await writer.drain()

    # Read response
    length_data = await reader.read(4)
    data_length = int.from_bytes(length_data, 'big')
    data = await reader.read(data_length)
    response = pickle.loads(data)

    writer.close()
    await writer.wait_closed()

    return pickle.loads(response.get('serialized_result'))
