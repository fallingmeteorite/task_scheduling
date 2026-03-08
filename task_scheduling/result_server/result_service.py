# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Task result server module.

This module provides a TCP server for storing and retrieving task results
using pickle serialization over asyncio streams.
"""

import asyncio
import threading
import time
from typing import Dict, Any, Optional, Tuple

import dill

from task_scheduling.common import logger, config


class ResultServer:
    """Server for managing task results storage and retrieval."""

    def __init__(self):
        """Initialize the result server with configuration."""
        self._running = None
        self.host = config["get_host"]
        self.port = config["get_port"]
        # Store task results and creation time (task_id: (result, create_time))
        self.tasks: Dict[str, Tuple[Any, float]] = {}
        self.lock = asyncio.Lock()
        self.server = None
        self._server_thread = None
        self._loop = None
        self.result_ttl = config["maximum_result_time_storage"]  # Task time-to-live in seconds
        self.cleanup_trigger_count = config["maximum_result_storage"] * 5  # Task count threshold for cleanup

    async def store_task_result(self, task_id: str, serialized_result: bytes):
        """Store task result in memory.

        Args:
            task_id: Unique identifier for the task
            serialized_result: Pickle-serialized task result
        """
        result = dill.loads(serialized_result)
        async with self.lock:
            self.tasks[task_id] = (result, time.time())

            # Trigger cleanup if storage threshold is reached
            if len(self.tasks) >= self.cleanup_trigger_count:
                logger.info(f"Task count reached cleanup threshold ({self.cleanup_trigger_count})")
                await self._perform_cleanup()

    async def get_task_result(self, task_id: str) -> Optional[bytes]:
        """Retrieve task result with timeout.

        Args:
            task_id: Unique identifier for the task

        Returns:
            Pickle-serialized result
        """
        poll_interval = 0.1  # Polling interval in seconds

        while True:
            async with self.lock:
                if task_id in self.tasks:
                    result, _ = self.tasks.pop(task_id)  # Retrieve and remove
                    return dill.dumps(result)

            await asyncio.sleep(poll_interval)

    async def _perform_cleanup(self):
        """Clean up expired and excess tasks from storage."""
        try:
            current_time = time.time()
            cleaned_count = 0

            async with self.lock:
                # Clean expired tasks (older than TTL)
                expired_tasks = [
                    task_id for task_id, (_, create_time) in self.tasks.items()
                    if current_time - create_time > self.result_ttl
                ]

                for task_id in expired_tasks:
                    del self.tasks[task_id]
                cleaned_count += len(expired_tasks)

                # If still over threshold, remove oldest tasks
                if len(self.tasks) >= self.cleanup_trigger_count:
                    # Sort tasks by creation time (oldest first)
                    sorted_tasks = sorted(
                        self.tasks.items(),
                        key=lambda x: x[1][1]  # Sort by create_time
                    )

                    # Calculate how many tasks need to be removed
                    excess_count = len(self.tasks) - self.cleanup_trigger_count
                    tasks_to_remove = min(excess_count, len(sorted_tasks))

                    # Remove oldest tasks
                    for i in range(tasks_to_remove):
                        task_id = sorted_tasks[i][0]
                        del self.tasks[task_id]

                    cleaned_count += tasks_to_remove

                    if tasks_to_remove > 0:
                        logger.info(f"Removed {tasks_to_remove} oldest tasks due to storage limit")

                # Log cleanup results
                if cleaned_count > 0:
                    logger.info(f"Total cleaned tasks: {cleaned_count}, remaining: {len(self.tasks)}")
                else:
                    logger.debug("No tasks required cleanup")

        except Exception as error:
            logger.error(f"Cleanup error: {error}")

    async def get_storage_info(self) -> Dict[str, Any]:
        """Get storage statistics and health information.

        Returns:
            Dictionary containing storage metrics
        """
        async with self.lock:
            current_time = time.time()
            task_ages = [current_time - create_time for _, create_time in self.tasks.values()]

            return {
                'total_tasks': len(self.tasks),
                'oldest_task_age': min(task_ages) if task_ages else 0,
                'newest_task_age': max(task_ages) if task_ages else 0,
                'is_over_threshold': len(self.tasks) >= self.cleanup_trigger_count,
                'cleanup_trigger_count': self.cleanup_trigger_count,
                'result_ttl': self.result_ttl,
            }

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle client connection and process requests.

        Args:
            reader: Stream reader for incoming data
            writer: Stream writer for outgoing data
        """
        try:
            # Read message length
            length_data = await reader.read(4)
            if not length_data:
                return

            data_length = int.from_bytes(length_data, 'big')

            # Read actual message data
            data = await reader.read(data_length)
            if not data:
                return

            # Deserialize request
            request = dill.loads(data)
            action = request['action']
            task_id = request.get('task_id')

            # Process different action types
            if action == 'store':
                serialized_result = request['serialized_result']
                await self.store_task_result(task_id, serialized_result)
                response = {'status': 'success'}

            elif action == 'get':
                serialized_result = await self.get_task_result(task_id)
                response = {
                    'status': 'success' if serialized_result else 'not_found',
                    'serialized_result': serialized_result
                }

            elif action == 'info':
                info = await self.get_storage_info()
                response = {'status': 'success', 'info': info}

            elif action == 'cleanup':
                await self._perform_cleanup()
                async with self.lock:
                    response = {
                        'status': 'success',
                        'remaining_count': len(self.tasks)
                    }

            elif action == 'set_trigger_count':
                if 'cleanup_trigger_count' in request:
                    self.cleanup_trigger_count = request['cleanup_trigger_count']
                response = {
                    'status': 'success',
                    'cleanup_trigger_count': self.cleanup_trigger_count
                }

            else:
                response = {'status': 'error', 'message': f'Unknown action: {action}'}

            # Serialize and send response
            response_data = dill.dumps(response)
            writer.write(len(response_data).to_bytes(4, 'big'))
            writer.write(response_data)
            await writer.drain()

        except Exception as error:
            logger.error(f"Client connection error: {error}")
            # Send error response
            error_response = dill.dumps({'status': 'error', 'message': str(error)})
            writer.write(len(error_response).to_bytes(4, 'big'))
            writer.write(error_response)
            await writer.drain()

        finally:
            writer.close()

    def _run_server(self):
        """Run server event loop in a separate thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def start_server():
            """Start the TCP server."""
            self.server = await asyncio.start_server(
                self.handle_client,
                self.host,
                self.port
            )
            logger.info(f'Result server running on {self.host}:{self.port}')

            async with self.server:
                await self.server.serve_forever()

        try:
            self._loop.run_until_complete(start_server())
        except Exception as error:
            logger.error(f"Server error: {error}")
        finally:
            self._loop.close()

    def start_server(self):
        """Start the server in a background thread."""
        if self._server_thread is None or not self._server_thread.is_alive():
            self._server_thread = threading.Thread(target=self._run_server, daemon=True)
            self._server_thread.start()

    def stop_server(self):
        """Stop the server gracefully."""
        if not self._loop or not self.server:
            return

        logger.info("Stopping result server...")
        self._running = False


# Global result server instance
result_server = ResultServer()
