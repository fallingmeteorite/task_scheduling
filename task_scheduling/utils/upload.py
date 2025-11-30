# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Task result storage module.

This module provides functionality for storing task results
to a remote server using custom protocol over TCP sockets.
"""

import asyncio
import pickle


def store_task_result(task_id: str, serialized_result: bytes, host='localhost', port=7998):
    """Store task result (synchronous function)

    Args:
        task_id: Task ID
        serialized_result: Already serialized task result
        host: Server host address
        port: Server port number
    """

    async def _async_store():
        request = {
            'action': 'store',
            'task_id': task_id,
            'serialized_result': serialized_result
        }

        reader, writer = await asyncio.open_connection(host, port)

        request_data = pickle.dumps(request)
        writer.write(len(request_data).to_bytes(4, 'big'))
        writer.write(request_data)
        await writer.drain()

        writer.close()
        await writer.wait_closed()

    asyncio.run(_async_store())