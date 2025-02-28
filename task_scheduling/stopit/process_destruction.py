# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import os
import queue
import threading
import time
from typing import Dict, Any

from ..common import logger


class ProcessTaskManager:
    __slots__ = ['_tasks',
                 '_operation_lock',  # Lock for dictionary operations
                 '_task_queue',
                 '_start'
                 ]

    def __init__(self, task_queue: queue.Queue) -> None:
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._operation_lock = threading.Lock()  # Lock for thread-safe dictionary operations
        self._task_queue = task_queue
        self._start: bool = True
        self._start_monitor_thread()  # Start the monitor thread

    def add(self, skip_obj: Any, task_id: str) -> None:
        """
        Add task control objects to the dictionary.
        :param skip_obj: An object that has a skip method.
        :param task_id: Task ID, used as the key in the dictionary.
        """
        with self._operation_lock:  # Lock for thread-safe dictionary access
            if task_id in self._tasks:
                logger.warning(f"Task with task_id '{task_id}' already exists, overwriting")
            self._tasks[task_id] = {
                'skip': skip_obj
            }

    def remove(self, task_id: str) -> None:
        """
        Remove the task and its associated data from the dictionary based on task_id.
        :param task_id: Task ID.
        """
        with self._operation_lock:  # Lock for thread-safe dictionary access
            if task_id in self._tasks:
                del self._tasks[task_id]
                if not self._tasks:  # Check if the tasks dictionary is empty
                    logger.info(f"Worker {os.getpid()} no tasks remaining, stopping the monitor thread")
                    self._start = False  # If tasks dictionary is empty, stop the loop

    def check(self, task_id: str) -> bool:
        """
        Check if the given task_id exists in the dictionary.
        :param task_id: Task ID.
        :return: True if the task_id exists, otherwise False.
        """
        with self._operation_lock:  # Lock for thread-safe dictionary access
            return task_id in self._tasks

    def skip_task(self, task_id: str) -> None:
        """
        Skip the task based on task_id.
        :param task_id: Task ID.
        """
        skip_obj = None
        with self._operation_lock:  # Lock for thread-safe dictionary access
            if task_id in self._tasks:
                skip_obj = self._tasks[task_id]['skip']
                del self._tasks[task_id]

        if skip_obj:
            try:
                skip_obj.skip()  # Perform the skip operation outside the lock
            except Exception as error:
                logger.error(f"Error skipping task '{task_id}': {error}")

    def _start_monitor_thread(self) -> None:
        """
        Start a thread to monitor the task queue and inject exceptions into task threads if the task_id matches.
        """
        threading.Thread(target=self._monitor_task_queue, daemon=True).start()

    def _monitor_task_queue(self) -> None:
        while self._start:
            try:
                task_id = self._task_queue.get(timeout=0.1)

                if isinstance(task_id, tuple):
                    self._task_queue.put(task_id)
                    continue

                if self.check(task_id):  # Check if the task_id exists in the dictionary
                    self.skip_task(task_id)  # Skip the task if it exists

                    with self._operation_lock:  # Lock for thread-safe dictionary access
                        if not self._tasks:  # Check if the tasks dictionary is empty
                            logger.info(f"Worker {os.getpid()} no tasks remaining, stopping the monitor thread")
                            break  # Stop the loop if tasks dictionary is empty
            except queue.Empty:
                pass  # Ignore empty queue exceptions
            except Exception as error:
                logger.error(f"Error in monitor thread: {error}")
            finally:
                time.sleep(0.4)
