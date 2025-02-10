# -*- coding: utf-8 -*-
# Author: fallingmeteorite

import os
import pickle
from typing import IO, Optional, Any, Dict

from ..common import logger


class TaskFunctionType:
    # Define cache_dict as a class variable
    cache_dict: Dict = {}

    @staticmethod
    def get_package_directory() -> str:
        """
        Get the directory path containing the __init__.py file.

        Returns:
            str: The path to the package directory.
        """
        return os.path.dirname(os.path.abspath(__file__))

    @classmethod
    def init_dict(cls) -> dict:
        """
        Initialize the dictionary by reading the pickle file.

        Returns:
            Dict: A dictionary containing task types.
        """
        try:
            with open(f"{cls.get_package_directory()}/task_type.pkl", 'rb') as file:
                return pickle.load(file)
        except FileNotFoundError:
            return {}

    @classmethod
    def append_to_dict(cls,
                       task_name: str,
                       function_type: str) -> None:
        """
        Append a task and its type to the dictionary and update the pickle file.

        Args:
            task_name (str): The name of the task.
            function_type (str): The type of the function.
        """
        tasks_dict = cls.init_dict()
        if task_name in tasks_dict:
            logger.info(f"The task name {task_name} already exists, updating its function type.")
        else:
            logger.info(f"The task name {task_name} does not exist, adding a new task.")
        tasks_dict[task_name] = function_type
        with open(f"{cls.get_package_directory()}/task_type.pkl", 'wb') as file:
            cls._write_to_file(file, tasks_dict)
        cls.cache_dict[task_name] = function_type
        logger.info(f"The task name {task_name} and its function type {function_type} have been added.")

    @classmethod
    def read_from_dict(cls,
                       task_name: str) -> Optional[str]:
        """
        Read the function type of a specified task name from the cache or pickle file.

        Args:
            task_name (str): The name of the task.

        Returns:
            Optional[str]: The function type of the task if it exists; otherwise, return None.
        """
        if task_name in cls.cache_dict:
            logger.info(f"Returning the function type for task name {task_name} from the cache.")
            return cls.cache_dict[task_name]
        else:
            logger.info(f"The task name {task_name} is not in the cache, reading from the file.")
            tasks_dict = cls.init_dict()
            cls.cache_dict = tasks_dict  # Update cache
            return tasks_dict.get(task_name, None)

    @staticmethod
    def _write_to_file(file: IO[Any],
                       data: dict) -> None:
        """
        Write data to a file in pickle format.

        Args:
            file (IO[Any]): The file object to write to.
            data (Dict): The data to write.
        """
        pickle.dump(data, file)
