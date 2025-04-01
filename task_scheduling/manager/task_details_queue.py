# -*- coding: utf-8 -*-
# Author: fallingmeteorite
from collections import OrderedDict, Counter
from typing import Dict, Optional, Union

from ..config import config


class TaskStatusManager:
    __slots__ = ['_task_status_dict', '_max_storage']

    def __init__(self) -> None:
        """
        Initialize the task status manager.
        """
        self._task_status_dict: OrderedDict[str, Dict[str, Optional[Union[str, float, bool]]]] = OrderedDict()
        self._max_storage = config["maximum_task_info_storage"]

    def add_task_status(self, task_id: str, task_name: str, status: Optional[str] = None,
                        start_time: Optional[float] = None,
                        end_time: Optional[float] = None, error_info: Optional[str] = None,
                        is_timeout_enabled: Optional[bool] = None) -> None:
        """
        Add or update task status information in the dictionary.

        Args:
            task_id (str): Task ID.
            task_name (str): Task Name.
            status (Optional[str]): Task status. If not provided, it is not updated.
            start_time (Optional[float]): The start time of the task in seconds. If not provided, the current time is used.
            end_time (Optional[float]): The end time of the task in seconds. If not provided, it is not updated.
            error_info (Optional[str]): Error information. If not provided, it is not updated.
            is_timeout_enabled (Optional[bool]): Boolean indicating if timeout processing is enabled. If not provided, it is not updated.
        """
        if task_id not in self._task_status_dict:
            self._task_status_dict[task_id] = {
                'task_name': None,
                'status': None,
                'start_time': None,
                'end_time': None,
                'error_info': None,
                'is_timeout_enabled': None
            }

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

        self._task_status_dict[task_id] = task_status
        if len(self._task_status_dict) > self._max_storage:
            self._clean_up()

    def _clean_up(self) -> None:
        """
        Clean up old task status entries if the dictionary exceeds the maximum storage limit.
        """
        # Remove old entries until the dictionary size is within the limit
        if len(self._task_status_dict) > self._max_storage:
            to_remove = []
            for k, v in self._task_status_dict.items():
                if v['status'] in ["failed", "completed", "timeout", "cancelled"]:
                    to_remove.append(k)
            for k in to_remove:
                self._task_status_dict.pop(k)

    def get_task_status(self,
                        task_id: str) -> Optional[Dict[str, Optional[Union[str, float, bool]]]]:
        """
        Retrieve task status information by task ID.

        Args:
            task_id (str): Task ID.

        Returns:
            Optional[Dict[str, Optional[Union[str, float, bool]]]]: Task status information as a dictionary, or None if the task ID is not found.
        """
        return self._task_status_dict.get(task_id)

    def get_all_task_statuses(self) -> Dict[str, Dict[str, Optional[Union[str, float, bool]]]]:
        """
        Retrieve all task status information.

        Returns:
            Dict[str, Dict[str, Optional[Union[str, float, bool]]]]: A copy of the dictionary containing all task status information.
        """
        return self._task_status_dict.copy()

    def get_task_count(self, task_name) -> int:
        """
        Args:
            task_name(str): Task name.

        Returns:
            int: The total number of tasks that exist

        """
        # initialize
        task_count = 0

        # Copy the dictionary to prevent the dictionary from being occupied
        _task_status_dict = self._task_status_dict.copy()

        for info in _task_status_dict.values():
            if info["task_name"] == task_name:
                task_count += 1

        return task_count

    def get_all_task_count(self) -> Dict[str, int]:

        """

        Returns:
            Dict[str, int]: The total amount of existence per task

        """
        # Copy the dictionary to prevent the dictionary from being occupied
        _task_status_dict = self._task_status_dict.copy()

        # Extract all task_name values
        values = []
        for inner_dict in _task_status_dict.values():
            value = inner_dict["task_name"]
            values.append(value)

        # Count occurrences and return as ordered dictionary
        return OrderedDict(Counter(values).most_common())
