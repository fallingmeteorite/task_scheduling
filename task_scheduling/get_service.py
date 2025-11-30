# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Task result server module.

This module provides a TCP server for storing and retrieving task results
using pickle serialization over asyncio streams.
"""

import asyncio
import pickle
import threading
import time
from typing import Dict, Any, Optional, Tuple
from task_scheduling.common import logger
from task_scheduling.common import config


class ResultServer:
    """Server for managing task results storage and retrieval."""

    def __init__(self, host='localhost', port=7998):
        self._running = None
        self.host = host
        self.port = port
        # Store task results and creation time (task_id: (result, create_time))
        self.tasks: Dict[str, Tuple[Any, float]] = {}
        self.lock = asyncio.Lock()
        self.server = None
        self._server_thread = None
        self._loop = None
        self.result_ttl = config[
            "maximum_result_time_storage"]  # Tasks will be cleaned up if not retrieved within 60 seconds
        self.cleanup_trigger_count = config["maximum_result_storage"] * 5  # Threshold count to trigger cleanup

    async def store_task_result(self, task_id: str, serialized_result: bytes):
        """Store task result in memory.

        Args:
            task_id: Unique identifier for the task
            serialized_result: Pickle-serialized task result
        """
        result = pickle.loads(serialized_result)
        async with self.lock:
            self.tasks[task_id] = (result, time.time())

            # Check if cleanup threshold is reached
            current_count = len(self.tasks)

            # Trigger cleanup if task count exceeds threshold
            if current_count >= self.cleanup_trigger_count:
                logger.info(
                    f"Task count ({current_count}) reached threshold ({self.cleanup_trigger_count}), triggering cleanup")
                await self._perform_cleanup()

    async def get_task_result(self, task_id: str, timeout: float = 30.0) -> Optional[bytes]:
        """Get task result with timeout.

        Args:
            task_id: Unique identifier for the task
            timeout: Maximum time to wait for result in seconds

        Returns:
            Pickle-serialized result or None if timeout
        """
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            async with self.lock:
                if task_id in self.tasks:
                    result, create_time = self.tasks.pop(task_id)  # Retrieve and delete
                    return pickle.dumps(result)

            await asyncio.sleep(0.1)

        return None

    async def _perform_cleanup(self):
        """Perform actual cleanup operation"""
        try:
            current_time = time.time()
            async with self.lock:
                # Clean up expired tasks (not retrieved within 60 seconds)
                expired_tasks = [
                    task_id for task_id, (_, create_time) in self.tasks.items()
                    if current_time - create_time > self.result_ttl
                ]
                for task_id in expired_tasks:
                    del self.tasks[task_id]

                # If still over threshold after cleaning expired tasks, clean oldest tasks by creation time
                current_count = len(self.tasks)
                if current_count >= self.cleanup_trigger_count:
                    # Sort by creation time, clean oldest tasks first
                    sorted_tasks = sorted(
                        self.tasks.items(),
                        key=lambda x: x[1][1]  # Sort by create_time
                    )
                    # Clean until below threshold
                    excess_count = current_count - self.cleanup_trigger_count

                    if excess_count > 0:
                        for i in range(excess_count):
                            if i < len(sorted_tasks):
                                task_id = sorted_tasks[i][0]
                                del self.tasks[task_id]

                        logger.info(f"Cleaned up {excess_count} oldest tasks due to storage limit")

                total_cleaned = len(expired_tasks) + (current_count - len(self.tasks))
                if total_cleaned > 0:
                    logger.info(f"Total cleaned tasks: {total_cleaned}, remaining: {len(self.tasks)}")
                else:
                    logger.debug("No tasks needed cleanup")

        except Exception as error:
            logger.error(f"Cleanup error: {error}")

    async def get_storage_info(self) -> Dict[str, Any]:
        """Get storage information for monitoring."""
        async with self.lock:
            current_time = time.time()
            task_ages = [current_time - create_time for _, create_time in self.tasks.values()]
            return {
                'total_tasks': len(self.tasks),
                'oldest_task_age': min(task_ages) if task_ages else 0,
                'newest_task_age': max(task_ages) if task_ages else 0,
                'is_over_threshold': len(self.tasks) >= self.cleanup_trigger_count,
                'cleanup_trigger_count': self.cleanup_trigger_count,
            }

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle client connection and process requests.

        Args:
            reader: Stream reader for incoming data
            writer: Stream writer for outgoing data
        """
        try:
            length_data = await reader.read(4)
            if not length_data:
                return

            data_length = int.from_bytes(length_data, 'big')
            data = await reader.read(data_length)
            if not data:
                return

            request = pickle.loads(data)
            action = request['action']
            task_id = request.get('task_id')

            if action == 'store':
                serialized_result = request['serialized_result']
                await self.store_task_result(task_id, serialized_result)
                response = {'status': 'success'}

            elif action == 'get':
                timeout = request.get('timeout', 30.0)
                serialized_result = await self.get_task_result(task_id, timeout)
                response = {
                    'status': 'success' if serialized_result else 'error',
                    'serialized_result': serialized_result
                }

            elif action == 'info':
                # Get storage information
                info = await self.get_storage_info()
                response = {'status': 'success', 'info': info}

            elif action == 'cleanup':
                # Manually trigger cleanup
                await self._perform_cleanup()
                async with self.lock:
                    response = {
                        'status': 'success',
                        'remaining_count': len(self.tasks)
                    }

            elif action == 'set_trigger_count':
                # Allow dynamic adjustment of trigger count
                if 'cleanup_trigger_count' in request:
                    self.cleanup_trigger_count = request['cleanup_trigger_count']
                response = {
                    'status': 'success',
                    'cleanup_trigger_count': self.cleanup_trigger_count
                }

            else:
                response = {'status': 'error', 'message': f'Unknown action: {action}'}

            response_data = pickle.dumps(response)
            writer.write(len(response_data).to_bytes(4, 'big'))
            writer.write(response_data)
            await writer.drain()

        except Exception as error:
            logger.error(f"Client connection error: {error}")
            # Send error response
            error_response = pickle.dumps({'status': 'error', 'message': str(error)})
            writer.write(len(error_response).to_bytes(4, 'big'))
            writer.write(error_response)
            await writer.drain()
        finally:
            writer.close()

    def _run_server(self):
        """Run server in a separate thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def start():
            self.server = await asyncio.start_server(
                self.handle_client,
                self.host,
                self.port
            )
            logger.info(f'Server running on {self.host}:{self.port}')
            async with self.server:
                await self.server.serve_forever()

        try:
            self._loop.run_until_complete(start())
        except Exception as error:
            logger.error(f"Server error: {error}")
        finally:
            self._loop.close()

    def start_server(self):
        """Start server (synchronous method)."""
        if self._server_thread is None or not self._server_thread.is_alive():
            self._server_thread = threading.Thread(target=self._run_server, daemon=True)
            self._server_thread.start()

    def stop_server(self):
        """Stop server (synchronous method)."""
        if not self._loop or not self.server:
            return

        logger.info("Stopping result server...")
        self._running = False


# Global result server instance
result_server = ResultServer()
