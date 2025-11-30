# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Server Core Module

Integrates core task execution, health monitoring, and connection handling functionality.
"""

import threading
import socket

from typing import Dict, Any, Callable, Tuple, Union
from task_scheduling.common import logger, config
from task_scheduling.utils import is_async_function
from task_scheduling.manager import task_scheduler
from task_scheduling.server_webui import get_tasks_info, start_task_status_ui


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
    Task Server Core Functionality
    """

    def __init__(self) -> None:
        """Initialize task server core."""
        self.health_monitor = ServerHealthMonitor()
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
            # Use unified network module to receive messages
            from task_scheduling.server.utils.network import receive_message

            message = receive_message(client_socket)
            if not message:
                logger.debug(f"No valid message received from {addr}")
                return

            message_type = message.get('type')
            logger.debug(f"Message received from {addr}: {message}")

            if message_type == 'execute_task':
                task_data = message.get('task_data', {})
                task_name = task_data.get('task_name', 'Unknown task')

                self.execute_received_task(task_data)
                logger.info(f"Task {task_name} execution completed")
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
        logger.info(f"Started connection handler for {addr}")

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
