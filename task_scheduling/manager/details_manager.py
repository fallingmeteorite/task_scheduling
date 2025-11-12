# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Task status management module.

This module provides a thread-safe task status manager for tracking and managing
the status of various tasks in a multithreaded environment.
"""
import time
import threading
import gc

from collections import OrderedDict, Counter
from typing import Dict, Optional, Union

from ..common import config, logger


class TaskStatusManager:
    """Manager for tracking task statuses in a thread-safe manner.

    This class provides functionality to add, remove, and query task status
    information with automatic cleanup and memory management.
    """
    __slots__ = ['_task_status_dict', '_max_storage', '_lock']

    def __init__(self) -> None:
        """
        Initialize the task status manager.
        """
        self._task_status_dict: OrderedDict[str, Dict[str, Optional[Union[str, float, bool]]]] = OrderedDict()
        self._max_storage = config["maximum_task_info_storage"]
        self._lock = threading.RLock()  # Reentrant lock for thread safety

    def add_task_status(self, task_id: str, task_name: str, status: Optional[str] = None,
                        start_time: Optional[float] = None,
                        end_time: Optional[float] = None, error_info: Optional[str] = None,
                        is_timeout_enabled: Optional[bool] = None,
                        task_type: str = None) -> None:
        """
        Add or update task status information in the dictionary.

        Args:
            task_id: Task ID.
            task_name: Task Name.
            status: Task status. If not provided, it is not updated.
            start_time: The start time of the task in seconds. If not provided, the current time is used.
            end_time: The end time of the task in seconds. If not provided, it is not updated.
            error_info: Error information. If not provided, it is not updated.
            is_timeout_enabled: Boolean indicating if timeout processing is enabled. If not provided, it is not updated.
            task_type: Task type. If not provided, it is not updated.
        """
        with self._lock:
            if task_id not in self._task_status_dict:
                if status not in ["failed", "completed", "timeout", "cancelled"]:
                    self._task_status_dict[task_id] = {
                        'task_name': None,
                        'status': None,
                        'start_time': None,
                        'end_time': None,
                        'error_info': None,
                        'is_timeout_enabled': None,
                        'task_type': None
                    }
                else:
                    return

            task_status = self._task_status_dict[task_id]

            if status is not None:
                task_status['status'] = status
            if task_name is not None:
                task_status['task_name'] = task_name
            if start_time is not None:
                task_status['start_time'] = start_time
            if end_time is not None:
                task_status['end_time'] = end_time
            if error_info is not None:
                task_status['error_info'] = error_info
            if is_timeout_enabled is not None:
                task_status['is_timeout_enabled'] = is_timeout_enabled
            if task_type is not None:
                task_status['task_type'] = task_type

            self._task_status_dict[task_id] = task_status

            if len(self._task_status_dict) > self._max_storage:
                self._clean_up()

            return

    def remove_task_status(self, task_name: str) -> None:
        """
        Remove all task status entries that are in "queuing" status and match the specified task name.

        Args:
            task_name: Task name to match for removal.
        """
        with self._lock:
            # Create a list of task IDs to remove
            to_remove = []

            for task_id, task_info in self._task_status_dict.items():
                if (task_info.get('task_name') == task_name and
                        task_info.get('status') == 'queuing'):
                    to_remove.append(task_id)

            # Remove the identified tasks
            for task_id in to_remove:
                self._task_status_dict.pop(task_id, None)
            del to_remove

    def _clean_up(self) -> None:
        """
        Clean up old task status entries if the dictionary exceeds the maximum storage limit.
        """
        with self._lock:
            # Remove old entries until the dictionary size is within the limit
            if len(self._task_status_dict) > self._max_storage:
                to_remove = []
                for k, v in self._task_status_dict.items():
                    if v['status'] in ["failed", "completed", "timeout", "cancelled"]:
                        to_remove.append(k)
                for k in to_remove:
                    self._task_status_dict.pop(k)
                del to_remove

        # Memory Cleanup
        logger.warning(f"Garbage collection performed. A total of <{gc.collect()}> objects were recycled.")

    def get_task_status(self,
                        task_id: str) -> Optional[Dict[str, Optional[Union[str, float, bool]]]]:
        """
        Retrieve task status information by task ID.

        Args:
            task_id: Task ID.

        Returns:
            Task status information as a dictionary, or None if the task ID is not found.
        """
        with self._lock:
            return self._task_status_dict.get(task_id)

    def get_task_type(self,
                      task_id: str) -> Optional[Dict[str, Optional[Union[str, float, bool]]]]:
        """
        Retrieve task status information by task ID.

        Args:
            task_id: Task ID.

        Returns:
            Task Type
        """
        while True:
            time.sleep(0.01)
            with self._lock:
                task_info = self._task_status_dict.get(task_id)
                if task_info and task_info["task_type"] != "NAN":
                    return task_info["task_type"]

    def get_all_task_statuses(self) -> Dict[str, Dict[str, Optional[Union[str, float, bool]]]]:
        """
        Retrieve all task status information.

        Returns:
            A copy of the dictionary containing all task status information.
        """
        with self._lock:
            return self._task_status_dict.copy()

    def get_task_count(self, task_name) -> int:
        """
        Get the count of tasks with the specified task name.

        Args:
            task_name: Task name.

        Returns:
            The total number of tasks that exist with the specified name.
        """
        with self._lock:
            # Initialize counter
            task_count = 0

            # Copy the dictionary to prevent the dictionary from being occupied
            _task_status_dict = self._task_status_dict.copy()

            for info in _task_status_dict.values():
                if info["task_name"] == task_name:
                    task_count += 1

            return task_count

    def get_all_task_count(self) -> Dict[str, int]:
        """
        Get the count of all tasks grouped by task name.

        Returns:
            The total count of tasks per task name.
        """
        with self._lock:
            # Copy the dictionary to prevent the dictionary from being occupied
            _task_status_dict = self._task_status_dict.copy()

            # Extract all task_name values
            values = []
            for inner_dict in _task_status_dict.values():
                value = inner_dict["task_name"]
                values.append(value)

            # Count occurrences and return as ordered dictionary
            return OrderedDict(Counter(values).most_common())

    def details_manager_shutdown(self) -> None:
        """Reset all variables"""
        with self._lock:
            self._task_status_dict = OrderedDict()
            self._max_storage = config["maximum_task_info_storage"]


# Shared by all schedulers, instantiating objects
task_status_manager = TaskStatusManager()
