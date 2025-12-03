# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Server Core Module with Network Utilities

Integrates server functionality with network communication, task execution,
health monitoring, and connection handling.
"""

import socket
import pickle
import time
import threading

from typing import Dict, Any, Callable, Tuple, Union, Optional
from task_scheduling.common import logger, config
from task_scheduling.utils import is_async_function
from task_scheduling.manager import task_scheduler
from task_scheduling.server_webui import get_tasks_info, start_task_status_ui


class NetworkUtils:
    """Network communication utilities."""

    @staticmethod
    def create_server_socket(host: str, port: int) -> Optional[socket.socket]:
        """
        Create and configure server socket.

        Args:
            host: Server host address
            port: Server port number

        Returns:
            Optional[socket.socket]: Configured server socket, None if failed
        """
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((host, port))
            server_socket.listen(5)
            server_socket.settimeout(1.0)
            return server_socket
        except Exception as e:
            logger.error(f"Failed to create server socket: {e}")
            return None

    @staticmethod
    def register_with_broker(broker_host: str, broker_port: int,
                             server_host: str, server_port: int) -> Optional[socket.socket]:
        """
        Register server with task broker.

        Args:
            broker_host: Broker host address
            broker_port: Broker port number
            server_host: Server host address
            server_port: Server port number

        Returns:
            Optional[socket.socket]: Broker socket connection, None if failed
        """
        try:
            broker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            broker_socket.connect((broker_host, broker_port))

            register_msg = {
                'type': 'server_register',
                'server_port': server_port,
                'host': server_host
            }

            data = pickle.dumps(register_msg)
            broker_socket.send(data)

            logger.info(f"Server registered with broker: {server_host}:{server_port}")
            return broker_socket

        except Exception as e:
            logger.error(f"Failed to register with broker: {e}")
            return None

    @staticmethod
    def send_message(socket_obj: socket.socket, message: Dict[str, Any]) -> bool:
        """
        Send message using length-prefix protocol.

        Args:
            socket_obj: Socket object
            message: Message dictionary to send

        Returns:
            bool: True if send successful, False otherwise
        """
        try:
            data = pickle.dumps(message)
            data_length = len(data)

            # Send length first (4 bytes), then data
            socket_obj.sendall(data_length.to_bytes(4, byteorder='big'))
            socket_obj.sendall(data)
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    @staticmethod
    def receive_message(socket_obj: socket.socket, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """
        Receive complete message (compatible with both length-prefix and direct pickle protocols).

        Args:
            socket_obj: Socket object
            timeout: Receive timeout in seconds

        Returns:
            Optional[Dict]: Received message, None on error
        """
        try:
            socket_obj.settimeout(timeout)

            # First try to receive 4 bytes as length prefix
            length_data = socket_obj.recv(4, socket.MSG_PEEK)  # Peek data without removing from buffer
            if not length_data:
                return None

            # Check if it's a reasonable length value (less than 10MB)
            potential_length = int.from_bytes(length_data, byteorder='big')
            if potential_length < 0 or potential_length > 10 * 1024 * 1024:  # 10MB limit
                # Likely direct pickle data without length prefix
                return NetworkUtils._receive_direct_pickle(socket_obj)
            else:
                # Use length-prefix protocol
                return NetworkUtils._receive_length_prefixed(socket_obj)

        except socket.timeout:
            return None
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            return None

    @staticmethod
    def _receive_length_prefixed(socket_obj: socket.socket) -> Optional[Dict[str, Any]]:
        """
        Receive message using length-prefix protocol.

        Args:
            socket_obj: Socket object

        Returns:
            Optional[Dict]: Received message
        """
        try:
            # Receive message length (first 4 bytes)
            length_data = socket_obj.recv(4)
            if not length_data:
                return None

            message_length = int.from_bytes(length_data, byteorder='big')

            # Receive actual message data
            message_data = b''
            while len(message_data) < message_length:
                chunk = socket_obj.recv(min(4096, message_length - len(message_data)))
                if not chunk:
                    break
                message_data += chunk

            if len(message_data) != message_length:
                logger.warning(f"Incomplete message: expected {message_length}, got {len(message_data)}")
                return None

            # Parse message
            message = pickle.loads(message_data)
            return message

        except Exception as e:
            logger.error(f"Error receiving length-prefixed message: {e}")
            return None

    @staticmethod
    def _receive_direct_pickle(socket_obj: socket.socket) -> Optional[Dict[str, Any]]:
        """
        Receive direct pickle data (without length prefix).

        Args:
            socket_obj: Socket object

        Returns:
            Optional[Dict]: Received message
        """
        try:
            message_data = b""
            socket_obj.settimeout(2.0)  # Set shorter timeout

            while True:
                try:
                    chunk = socket_obj.recv(4096)
                    if not chunk:
                        break
                    message_data += chunk
                    # Try to parse pickle to check if message is complete
                    try:
                        message = pickle.loads(message_data)
                        return message
                    except (pickle.UnpicklingError, EOFError):
                        # Message not complete yet, continue receiving
                        continue
                except socket.timeout:
                    # Timeout, consider message reception complete
                    break

            # Final parsing attempt
            if message_data:
                try:
                    message = pickle.loads(message_data)
                    return message
                except (pickle.UnpicklingError, EOFError) as e:
                    logger.error(f"Failed to parse direct pickle data: {e}")
                    return None

            return None

        except Exception as e:
            logger.error(f"Error receiving direct pickle message: {e}")
            return None

    @staticmethod
    def create_health_message(health_score: int) -> Dict[str, Any]:
        """
        Create health check response message.

        Args:
            health_score: Health score

        Returns:
            Dict: Health check message
        """
        return {
            'type': 'health_response',
            'health_score': health_score,
            'timestamp': time.time()
        }

    @staticmethod
    def create_task_message(task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create task message.

        Args:
            task_data: Task data

        Returns:
            Dict: Task message
        """
        return {
            'type': 'execute_task',
            'task_data': task_data
        }


class ServerHealthMonitor:
    """
    Server Health Status Monitor
    """

    def __init__(self) -> None:
        self.max_capacity: int = config["io_liner_task"] + config["timer_task"] + config["cpu_asyncio_task"] * config[
            "maximum_event_loop"]

    def get_health_percentage(self) -> int:
        """
        Calculate server health status percentage.

        Returns:
            int: Health status percentage (0-100)
        """
        task_status = get_tasks_info()

        if not task_status:
            return 0

        # Extract various metrics
        queue_size = task_status.get('queue_size', 0)
        running_count = task_status.get('running_count', 0)
        failed_count = task_status.get('failed_count', 0)
        completed_count = task_status.get('completed_count', 0)

        # Calculate total tasks
        total_tasks = queue_size + running_count + failed_count + completed_count

        if total_tasks == 0:
            return 100

        # Calculate weighted scores for each metric
        queue_score = max(0, 100 - (queue_size / self.max_capacity) * 100)

        if running_count <= self.max_capacity * 0.8:
            running_score = 100
        else:
            running_score = max(0, 100 - ((running_count - self.max_capacity * 0.8) / (self.max_capacity * 0.2)) * 100)

        failed_score = max(0, 100 - (failed_count / total_tasks) * 100)
        completed_score = (completed_count / total_tasks) * 100

        # Calculate comprehensive health score
        health_percentage = (
                queue_score * 0.2 +
                running_score * 0.4 +
                failed_score * 0.3 +
                completed_score * 0.1
        )

        health_percentage = max(0, min(100, int(health_percentage)))
        return health_percentage


def task_submit(task_id: str, delay: Union[int, None], daily_time: Union[str, None], function_type: str,
                timeout_processing: bool, task_name: str, func: Callable, priority: str,
                *args, **kwargs) -> None:
    """
    Submit task to queue.

    Args:
        task_id: Task ID
        delay: Delay time
        daily_time: Daily execution time
        function_type: Function type
        timeout_processing: Whether to enable timeout processing
        task_name: Task name
        func: Task function
        priority: Task priority
        args: Positional arguments
        kwargs: Keyword arguments
    """
    async_function = is_async_function(func)
    if async_function and not function_type == "timer":
        task_scheduler.add_task(None, None, async_function, function_type, timeout_processing,
                                task_name, task_id, func, priority, *args, **kwargs)

    if not async_function and not function_type == "timer":
        task_scheduler.add_task(None, None, async_function, function_type, timeout_processing,
                                task_name, task_id, func, priority, *args, **kwargs)

    if function_type == "timer":
        task_scheduler.add_task(delay, daily_time, async_function, function_type, timeout_processing,
                                task_name, task_id, func, priority, *args, **kwargs)


class TaskServerCore:
    """
    Task Server Core Functionality with Integrated Network Utilities
    """

    def __init__(self) -> None:
        """Initialize task server core."""
        self.health_monitor = ServerHealthMonitor()
        self.network_utils = NetworkUtils()
        # Start task status Web UI
        start_task_status_ui()

    def execute_received_task(self, task_data: Dict[str, Any]) -> None:
        """
        Execute received task.

        Args:
            task_data: Dictionary containing task information
        """
        try:
            # Extract task parameters
            function_code = task_data.get('function_code')
            function_name = task_data.get('function_name')
            args = task_data.get('args', ())
            kwargs = task_data.get('kwargs', {})
            task_name = task_data.get('task_name', 'Unnamed task')
            task_id = task_data.get('task_id', 'unknown')

            # Get task scheduling parameters
            delay = task_data.get('delay')
            daily_time = task_data.get('daily_time')
            function_type = task_data.get('function_type', 'normal')
            timeout_processing = task_data.get('timeout_processing', False)
            priority = task_data.get('priority', 'normal')

            # Validate required parameters
            if not function_code or not function_name:
                logger.error("Function code or function name not provided")
                return

            # Create namespace and execute function code
            namespace = {}
            compiled_code = compile(function_code, '<string>', 'exec')
            exec(compiled_code, namespace)

            # Get function object
            func = namespace.get(function_name)
            if not func or not callable(func):
                logger.error(f"Function '{function_name}' not found or not callable")
                return

            # Submit task to scheduler
            task_submit(
                task_id, delay, daily_time, function_type, timeout_processing,
                task_name, func, priority, *args, **kwargs
            )

            logger.info(f"Task '{task_name}' submitted successfully")

        except Exception as e:
            logger.error(f"Task execution failed: {e}")

    def handle_client_connection(self, client_socket: socket.socket, addr: Tuple) -> None:
        """
        Handle client connection and process incoming tasks (using unified protocol).

        Args:
            client_socket: Client socket object
            addr: Client address tuple (host, port)
        """
        try:
            message = self.network_utils.receive_message(client_socket)
            if not message:
                return

            message_type = message.get('type')

            if message_type == 'execute_task':
                task_data = message.get('task_data', {})
                task_name = task_data.get('task_name', 'Unknown task')

                self.execute_received_task(task_data)
                logger.info(f"Task {task_name} executed successfully from {addr[0]}:{addr[1]}")
            else:
                logger.warning(f"Unexpected message type from {addr}: {message_type}")

        except Exception as e:
            logger.error(f"Error handling client connection {addr}: {e}")
        finally:
            client_socket.close()

    def start_connection_handler(self, client_socket: socket.socket, addr: Tuple) -> None:
        """
        Start thread to handle client connection.

        Args:
            client_socket: Client socket object
            addr: Client address tuple
        """
        client_thread = threading.Thread(
            target=self.handle_client_connection,
            args=(client_socket, addr), daemon=True
        )
        client_thread.start()

    def get_health_status(self) -> int:
        """
        Get server health status.

        Returns:
            int: Health status percentage
        """
        return self.health_monitor.get_health_percentage()

    def shutdown(self) -> None:
        """Shutdown task scheduler"""
        task_scheduler.shutdown_scheduler()