# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Task Serialization Module

Handles task data serialization and function code extraction for distributed task processing.
"""

import inspect
import time

from typing import Dict, Any, Callable, Optional, Union
from task_scheduling.common import logger


class TaskSerializer:
    """
    Handles task data serialization and preparation for transmission to proxy server.

    Provides methods to extract function information and create structured task data
    packages that can be serialized and transmitted to remote execution environments.
    """

    @staticmethod
    def extract_function_info(func: Optional[Callable]) -> tuple[str, str]:
        """
        Extract function source code and name for remote execution.

        Uses Python's inspect module to retrieve the source code of callable functions
        to enable execution in remote environments.

        Args:
            func: Callable function object to analyze and extract

        Returns:
            tuple: Contains (function_code, function_name) as strings
                  Returns empty strings if extraction fails

        Raises:
            Logs warnings for non-callable objects or extraction failures
        """
        function_code = ""
        function_name = ""

        if callable(func):
            try:
                function_code = inspect.getsource(func)
                function_name = func.__name__
            except (TypeError, OSError) as error:
                logger.error(f"Failed to extract function source: {error}")

        return function_code, function_name

    @staticmethod
    def create_task_data(
            task_id: str,
            task_name: str,
            function_code: str,
            function_name: str,
            delay: Union[int, None],
            daily_time: Union[str, None],
            function_type: str,
            timeout_processing: bool,
            priority: str,
            *args, **kwargs) -> Dict[str, Any]:
        """
        Create comprehensive task data package for serialization.

        Constructs a complete task dictionary containing all necessary information
        for remote execution including timing, priority, and function details.

        Args:
            task_id: Unique task identifier string
            task_name: Descriptive name for the task
            function_code: Source code of the function to execute
            function_name: Name of the function to execute
            delay: Optional delay in seconds before execution
            daily_time: Optional daily scheduled time string (HH:MM format)
            function_type: Type classification of function (default: "normal")
            timeout_processing: Flag indicating if timeout processing is enabled
            priority: Task priority level (default: "normal")
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Dict[str, Any]: Complete task data dictionary ready for serialization
        """
        task_data = {
            'task_id': task_id,
            'task_name': task_name,
            'delay': delay,
            'daily_time': daily_time,
            'function_type': function_type,
            'timeout_processing': timeout_processing,
            'priority': priority,
            'function_code': function_code,
            'function_name': function_name,
            'args': args,
            'kwargs': kwargs,
            'submit_time': time.time(),  # Timestamp when task was created
        }
        return task_data

    @staticmethod
    def create_request_payload(task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create proxy server request payload with proper message type.

        Wraps task data in a standardized request structure that identifies
        the message type for the proxy server's request handler.

        Args:
            task_data: Complete task data dictionary from create_task_data()

        Returns:
            Dict[str, Any]: Request payload ready for network transmission
        """
        payload = {
            'type': 'client_submit_task',  # Identifies message type to proxy
            'task_data': task_data,
        }
        return payload
