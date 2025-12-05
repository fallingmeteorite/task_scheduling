# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Simple RPC Client with Direct Function Calls and Proper Serialization
"""

import socket
from typing import Any, Dict

from task_scheduling.client.utils import NetworkHandler
from task_scheduling.common import logger, config


class RPCClient:
    """
    Simple RPC Client for direct function calls with proper serialization.

    Usage:
        with RPCClient('localhost', 8888) as client:
            info = client.get_tasks_info()
            client.add_ban_task_name('bad_task')
            client.pause_api('video', 'task_123')
    """

    def __init__(self):
        """
        Initialize RPC client.
        """
        self._socket = None
        self.host = config["control_host"]
        self.port = config["control_ip"]
        self._network = NetworkHandler()
        self._socket: socket.socket
        self._connected = False

    def add_ban_task_name(self, task_name: str) -> bool:
        """
        Add a task name to the ban list.

        Args:
            task_name: Name of task to ban

        Returns:
            bool: True if successful
        """
        return self._rpc_call('add_ban_task_name', task_name)

    def remove_ban_task_name(self, task_name: str) -> bool:
        """
        Remove a task name from the ban list.

        Args:
            task_name: Name of task to unban

        Returns:
            bool: True if successful
        """
        return self._rpc_call('remove_ban_task_name', task_name)

    def cancel_the_queue_task_by_name(self, task_name: str) -> bool:
        """
        Cancel queued task by name.

        Args:
            task_name: Name of task to cancel

        Returns:
            bool: True if successful
        """
        return self._rpc_call('cancel_the_queue_task_by_name', task_name)

    def get_tasks_info(self) -> Dict[str, Any]:
        """
        Get information about all tasks.

        Returns:
            Dict[str, Any]: Task information
        """
        return self._rpc_call('get_tasks_info')

    def get_task_status(self, task_name: str) -> Dict[str, Any]:
        """
        Get status of specific task.

        Args:
            task_name: Name of task

        Returns:
            Dict[str, Any]: Task status information
        """
        return self._rpc_call('get_task_status', task_name)

    def get_task_count(self) -> Dict[str, int]:
        """
        Get task counts by status.

        Returns:
            Dict[str, int]: Task counts
        """
        return self._rpc_call('get_task_count')

    def get_all_task_count(self) -> Dict[str, Any]:
        """
        Get all task count information.

        Returns:
            Dict[str, Any]: Complete task count information
        """
        return self._rpc_call('get_all_task_count')

    def pause_api(self, task_type: str, task_id: str) -> bool:
        """
        Pause a running task.

        Args:
            task_type: Type of the task (e.g., 'video', 'image', etc.)
            task_id: ID of the task to pause

        Returns:
            bool: True if successful, False otherwise
        """
        return self._rpc_call('pause_api', task_type, task_id)

    def resume_api(self, task_type: str, task_id: str) -> bool:
        """
        Resume a paused task.

        Args:
            task_type: Type of the task (e.g., 'video', 'image', etc.)
            task_id: ID of the task to resume

        Returns:
            bool: True if successful, False otherwise
        """
        return self._rpc_call('resume_api', task_type, task_id)

    def kill_api(self, task_type: str, task_id: str) -> bool:
        """
        Kill (terminate) a task.

        Args:
            task_type: Type of the task (e.g., 'video', 'image', etc.)
            task_id: ID of the task to kill

        Returns:
            bool: True if successful, False otherwise
        """
        return self._rpc_call('kill_api', task_type, task_id)

    def _rpc_call(self, func_name: str, *args, **kwargs) -> Any:
        """
        Execute remote function call with proper serialization.

        Args:
            func_name: Name of remote function
            *args: Positional arguments (will be serialized)
            **kwargs: Keyword arguments (will be serialized)

        Returns:
            Any: Result from remote function

        Raises:
            ConnectionError: If you cannot connect to server
            RuntimeError: If remote call fails
        """
        # Ensure connection
        if not self._connected:
            self.connect()

        try:
            # Prepare request (will be serialized by network handler)
            request = {
                'function': func_name,
                'args': args,
                'kwargs': kwargs
            }

            # Send request (network handler handles serialization)
            if not self._network.send_message(self._socket, request):
                raise ConnectionError(f"Failed to send request for {func_name}")

            # Receive response (network handler handles deserialization)
            response = self._network.receive_message(self._socket)
            if response is None:
                raise ConnectionError(f"No response for {func_name}")

            # Check for errors
            if not response.get('success', False):
                error_msg = response.get('error', 'Unknown error')
                raise RuntimeError(f"{func_name} failed: {error_msg}")

            # Return result (already deserialized)
            return response.get('result')

        except socket.error as e:
            self._connected = False
            raise ConnectionError(f"Network error in {func_name}: {e}")
        except Exception as e:
            raise RuntimeError(f"RPC call {func_name} failed: {e}")

    def connect(self):
        """
        Connect to RPC server.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            self._socket = self._network.create_client_socket(self.host, self.port)
            if self._socket:
                self._connected = True
                logger.info(f"Connected to {self.host}:{self.port}")
            else:
                raise ConnectionError(f"Failed to connect to {self.host}:{self.port}")
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Connection failed: {e}")

    def disconnect(self):
        """Disconnect from server."""
        if self._socket:
            self._socket.close()
            self._socket = None
            self._connected = False

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def __del__(self):
        """Cleanup on deletion."""
        self.disconnect()
