# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Task function type management module.

This module provides functionality to store and retrieve task function types
using persistent pickle storage with in-memory caching for performance.
"""
import os
import pickle

from typing import IO, Optional, Any, Dict


class TaskFunctionType:
    """Manager for task function type storage and retrieval.

    This class provides methods to persistently store task function types
    (e.g., 'io', 'cpu', 'timer') and retrieve them with caching for efficiency.
    """
    # Define cache_dict as a class variable
    _cache_dict: Dict = {}

    @staticmethod
    def _get_package_directory() -> str:
        """
        Get the directory path containing the __init__.py file.

        Returns:
            The path to the package directory.
        """
        return os.path.dirname(os.path.abspath(__file__))

    @classmethod
    def _init_dict(cls) -> dict:
        """
        Initialize the dictionary by reading the pickle file.

        Returns:
            A dictionary containing task types.
        """
        try:
            with open(f"{cls._get_package_directory()}/task_type.pkl", 'rb') as _file:
                return pickle.load(_file)
        except FileNotFoundError:
            return {}

    @classmethod
    def append_to_dict(cls,
                       task_name: str,
                       function_type: str) -> None:
        """
        Append a task and its type to the dictionary and update the pickle file.

        Args:
            task_name: The name of the task.
            function_type: The type of the function.
        """
        _tasks_dict = cls._init_dict()
        _tasks_dict[task_name] = function_type
        with open(f"{cls._get_package_directory()}/task_type.pkl", 'wb') as file:
            cls._write_to_file(file, _tasks_dict)
        cls._cache_dict[task_name] = function_type

    @classmethod
    def read_from_dict(cls,
                       task_name: str) -> Optional[str]:
        """
        Read the function type of specified task name from the cache or pickle file.

        Args:
            task_name: The name of the task.

        Returns:
            Optional: The function type of the task if it exists; otherwise, return None.
        """
        if task_name in cls._cache_dict:
            return cls._cache_dict[task_name]
        else:
            _tasks_dict = cls._init_dict()
            cls._cache_dict = _tasks_dict  # Update cache
            return _tasks_dict.get(task_name, None)

    @staticmethod
    def _write_to_file(_file: IO[Any],
                       _data: dict) -> None:
        """
        Write data to a file in pickle format.

        Args:
            _file: The file object to write to.
            _data: The data to write.
        """
        pickle.dump(_data, _file)


task_function_type = TaskFunctionType
