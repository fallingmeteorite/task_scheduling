# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Task Manager Module

This module provides a comprehensive task management system for handling task submission,
queue management, and task history tracking.

Key Features:
    - Task submission with server-side metadata
    - Task validation and integrity checking
    - Task queue management with retry capability
    - Task history tracking and statistics

Classes:
    TaskManager: Main class for managing task lifecycle and operations

Global Variables:
    None
"""

import time

from typing import Dict, Any, Optional, List


class TaskManager:
    """
    Task Management - All task-related operations are centralized here.

    This class provides a complete task management solution including task submission,
    queue management, history tracking, and statistical reporting.

    Attributes:
        task_queue: List of pending tasks awaiting execution
        task_history: Dictionary tracking all submitted tasks with their status

    Methods:
        submit_task: Submit a new task with server-side metadata
        validate_task_data: Validate task data integrity and completeness
        get_pending_task: Retrieve the next pending task from the queue
        requeue_task: Requeue a task for retry with updated metadata
        complete_task: Mark a task as completed with optional result
        get_task_by_id: Retrieve a specific task by its unique identifier
        get_task_stats: Generate statistics about current task state
    """

    def __init__(self) -> None:
        """
        Initialize TaskManager with empty task queue and history.

        Initializes:
            task_queue: Empty list for pending tasks
            task_history: Empty dictionary for task history tracking
        """
        self.task_queue: List[Dict[str, Any]] = []
        self.task_history: Dict[str, Dict] = {}  # Task history records

    def submit_task(self, task_data: Dict) -> str:
        """
        Submit task - using client-provided task_id.

        This method accepts task data, validates it, adds server-side metadata,
        and places the task in the execution queue.

        Args:
            task_data: Dictionary containing task information including:
                - task_id: Unique identifier for the task (required)
                - task_name: Descriptive name of the task
                - function_code: Code to be executed
                - function_name: Name of the function to execute

        Returns:
            str: The task_id if submission successful, empty string otherwise
        """
        task_id = task_data.get('task_id')
        if not task_id:
            return ""

        # Add server-side metadata
        task_data.update({
            'submit_time': time.time(),
            'queue_time': time.time(),
            'status': 'queued'
        })

        self.task_queue.append(task_data)
        self.task_history[task_id] = task_data
        return task_id

    def validate_task_data(self, task_data: Dict) -> bool:
        """
        Validate task data completeness and integrity.

        Checks that all required fields are present in the task data
        to ensure successful task execution.

        Args:
            task_data: Dictionary containing task information to validate

        Returns:
            bool: True if task data is valid, False otherwise

        Note:
            Required fields: task_id, task_name, function_code, function_name
        """
        required_fields = ['task_id', 'task_name', 'function_code', 'function_name']
        missing_fields = [field for field in required_fields if not task_data.get(field)]

        if missing_fields:
            return False
        return True

    def get_pending_task(self) -> Optional[Dict]:
        """
        Get next pending task from queue.

        Retrieves and removes the next task from the front of the task queue.

        Returns:
            Optional[Dict]: Next task data if available, None if queue is empty
        """
        return self.task_queue.pop(0) if self.task_queue else None

    def requeue_task(self, task_data: Dict) -> None:
        """
        Requeue task for retry with updated metadata.

        This method is used when a task needs to be retried, updating
        retry counters and status before placing it back in the queue.

        Args:
            task_data: Dictionary containing the task data to requeue

        Returns:
            None
        """
        retry_count = task_data.get('retry_count', 0) + 1

        task_data.update({
            'retry_count': retry_count,
            'last_retry': time.time(),
            'status': 'retrying'
        })

        self.task_queue.insert(0, task_data)

    def complete_task(self, task_id: str, result: Any = None) -> None:
        """
        Mark task as completed with optional result.

        Updates the task status in history to completed and records
        the completion time and any result data.

        Args:
            task_id: Unique identifier of the task to complete
            result: Optional result data from task execution

        Returns:
            None
        """
        if task_id in self.task_history:
            self.task_history[task_id].update({
                'status': 'completed',
                'complete_time': time.time(),
                'result': result
            })

    def get_task_by_id(self, task_id: str) -> Optional[Dict]:
        """
        Get task by task_id from history.

        Retrieves a specific task's data from the task history using
        its unique identifier.

        Args:
            task_id: Unique identifier of the task to retrieve

        Returns:
            Optional[Dict]: Task data if found, None otherwise
        """
        return self.task_history.get(task_id)

    def get_task_stats(self) -> Dict:
        """
        Get task statistics.

        Generates comprehensive statistics about the current state
        of tasks in the system.

        Returns:
            Dict: Statistics including:
                - queued: Number of tasks in queue
                - total_history: Total tasks in history
                - completed: Number of completed tasks
        """
        return {
            'queued': len(self.task_queue),
            'total_history': len(self.task_history),
            'completed': len([t for t in self.task_history.values() if t.get('status') == 'completed'])
        }
