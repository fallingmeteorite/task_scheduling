# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Task Submission Client Module

This module provides client-side functions for submitting tasks to the proxy server.
It allows asynchronous task submission without waiting for execution results.

Key Features:
    - Asynchronous task submission with fire-and-forget semantics
    - Function serialization and transmission
    - Task metadata management
    - Error handling and logging

Functions:
    submit_function_task: Main function for submitting task execution requests

Global Variables:
    _serializer: Global TaskSerializer instance for task data preparation
"""

import uuid

from typing import Callable, Optional, Union
from task_scheduling.common import logger
from task_scheduling.client.utils import TaskSerializer, send_request
from task_scheduling.utils import wait_branch_thread_ended_check

# Create global serializer instance for consistent task serialization
_serializer = TaskSerializer()


def submit_function_task(
        delay: Union[int, None],
        daily_time: Union[str, None],
        function_type: str,
        timeout_processing: bool,
        task_name: str,
        func: Optional[Callable],
        priority: str,
        *args, **kwargs) -> Union[str, None]:
    """
    Submit function execution task without waiting for result (fire-and-forget).

    This function prepares and submits a task for remote execution by serializing
    the function code and task metadata, then sending it to the proxy server.
    The function returns immediately after submission without waiting for execution.

    Args:
        delay: Delay execution time in seconds (None for immediate execution)
        daily_time: Daily scheduled time in "HH:MM" format for recurring tasks
        function_type: Type of function ("normal", "periodic", "scheduled")
        timeout_processing: Whether to enable timeout processing for long-running tasks
        task_name: Descriptive name for the task for monitoring purposes
        func: Callable function to execute (must be provided for execution)
        priority: Task priority level ("low", "normal", "high", "critical")
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        str: Unique task ID string that can be used for task reference and tracking

    Raises:
        Logs errors but doesn't raise exceptions to maintain fire-and-forget semantics

    Note:
        Uses fire-and-forget approach - delivery and execution are not guaranteed.
        Function source code must be available for serialization (no lambda functions).
    """
    if wait_branch_thread_ended_check(func):
        if not function_type == "cpu":
            logger.error("Experimental tasks must specify function type as FUNCTION_TYPE_CPU!")
            return None

    try:
        # Validate that a callable function is provided
        if not func or not callable(func):
            logger.error(f"Invalid function provided for task '{task_name}'")
            return None

        # Extract function information using serializer
        function_code, function_name = _serializer.extract_function_info(func)

        if not function_code:
            logger.error(f"Empty function code extracted for task '{task_name}'")
            return None

        # Generate unique task identifier for tracking
        task_id = str(uuid.uuid4())

        # Create comprehensive task data package
        task_data = _serializer.create_task_data(
            task_id,
            task_name,
            function_code,
            function_name,
            delay,
            daily_time,
            function_type,
            timeout_processing,
            priority,
            *args, **kwargs
        )

        # Create request payload for proxy server
        request_payload = _serializer.create_request_payload(task_data)

        # Send request asynchronously (fire-and-forget)
        send_request(request_payload)

        logger.debug(f"Task ID: {task_id} submitted successfully")
        return task_id

    except Exception as error:
        # Log error but return task_id to maintain interface consistency
        logger.error(f"Task ID: {task_id} submission failed: {error}")
        return None
