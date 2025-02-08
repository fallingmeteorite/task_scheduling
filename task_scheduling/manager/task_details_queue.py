from collections import OrderedDict
from typing import Dict, Optional, Union

from ..config import config


class TaskStatusManager:
    __slots__ = ['task_status_dict', 'max_storage']

    def __init__(self, max_storage: int = config["maximum_task_info_storage"]):
        """
        Initialize the task status manager.

        :param max_storage: Maximum number of task status entries to store.

        """
        self.task_status_dict: OrderedDict[str, Dict[str, Optional[Union[str, float, bool]]]] = OrderedDict()
        self.max_storage = max_storage

    def add_task_status(self, task_id: str, task_name: str, status: Optional[str] = None,
                        start_time: Optional[float] = None,
                        end_time: Optional[float] = None, error_info: Optional[str] = None,
                        is_timeout_enabled: Optional[bool] = None) -> None:
        """
        Add or update task status information in the dictionary.
        :param task_name: Task Name.
        :param task_id: Task ID.
        :param status: Task status. If not provided, it is not updated.
        :param start_time: The start time of the task in seconds. If not provided, the current time is used.
        :param end_time: The end time of the task in seconds. If not provided, it is not updated.
        :param error_info: Error information. If not provided, it is not updated.
        :param is_timeout_enabled: Boolean indicating if timeout processing is enabled. If not provided, it is not updated.
        """
        if task_id not in self.task_status_dict:
            self.task_status_dict[task_id] = {
                'task_name': None,
                'status': None,
                'start_time': None,
                'end_time': None,
                'error_info': None,
                'is_timeout_enabled': None
            }

        task_status = self.task_status_dict[task_id]

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

        self.task_status_dict[task_id] = task_status
        if len(self.task_status_dict) > self.max_storage:
            self._clean_up()

    def _clean_up(self) -> None:
        """
        Clean up old task status entries if the dictionary exceeds the maximum storage limit.
        """
        # Remove old entries until the dictionary size is within the limit
        if len(self.task_status_dict) > self.max_storage:
            to_remove = []
            for k, v in self.task_status_dict.items():
                if v['status'] in ["failed", "completed", "timeout", "cancelled"]:
                    to_remove.append(k)
            for k in to_remove:
                self.task_status_dict.pop(k)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Optional[Union[str, float, bool]]]]:
        """
        Retrieve task status information by task ID.

        :param task_id: Task ID.
        :return: Task status information as a dictionary, or None if the task ID is not found.
        """
        return self.task_status_dict.get(task_id)

    def get_all_task_statuses(self) -> Dict[str, Dict[str, Optional[Union[str, float, bool]]]]:
        """
        Retrieve all task status information.

        :return: A copy of the dictionary containing all task status information.
        """
        return self.task_status_dict.copy()
