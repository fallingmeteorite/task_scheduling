# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Simple RPC Client with Direct Function Calls and Proper Serialization
"""

import functools
import socket
from typing import Any

from task_scheduling.client.utils import NetworkHandler
from task_scheduling.common import logger, config


class RPCClient:
    """
    Simple RPC Client for direct function calls with proper serialization.

    Usage:
        with RPCClient('localhost', 8888) as client:
            info = client.get_tasks_info()
            client.add_ban_task_name('bad_task')
    """

    # List of available RPC functions
    AVAILABLE_FUNCTIONS = [
        'add_ban_task_name',
        'remove_ban_task_name',
        'cancel_the_queue_task_by_name',
        'get_tasks_info',
        'get_task_status',
        'get_task_count',
        'get_all_task_count',
    ]

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

        # Dynamically create all available functions
        self._create_dynamic_functions()

    def _create_dynamic_functions(self):
        """Create dynamic methods for all available RPC functions."""
        for func_name in self.AVAILABLE_FUNCTIONS:
            # Create the function
            def make_function(name):
                @functools.wraps(self._rpc_call)
                def rpc_function(*args, **kwargs):
                    return self._rpc_call(name, *args, **kwargs)

                rpc_function.__name__ = name
                rpc_function.__doc__ = f"Call remote function: {name}"
                return rpc_function

            # Add the function as a method
            setattr(self, func_name, make_function(func_name))

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
