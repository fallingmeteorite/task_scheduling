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
    submit_task: Main function for submitting task execution requests

Global Variables:
    _serializer: Global TaskSerializer instance for task data preparation
"""
import inspect
import uuid
from typing import Dict, Any, Callable, Optional, Union

from task_scheduling.client.utils import send_request
from task_scheduling.common import logger
from task_scheduling.utils import wait_branch_thread_ended_check


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
    }
    return task_data


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


def submit_task(
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

    # Generate unique task identifier for tracking
    task_id = str(uuid.uuid4())

    try:
        # Extract function information using serializer
        function_code, function_name = extract_function_info(func)

        # Create comprehensive task data package
        task_data = create_task_data(
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
        request_payload = create_request_payload(task_data)

        # Send request asynchronously (fire-and-forget)
        send_request(request_payload)

        logger.debug(f"Task ID: {task_id} submitted successfully")
        return task_id

    except Exception as error:
        # Log error but return task_id to maintain interface consistency
        logger.error(f"Task ID: {task_id} submission failed: {error}")
        return None
