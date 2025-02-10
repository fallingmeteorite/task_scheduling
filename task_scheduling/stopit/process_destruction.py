# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import queue
import threading
from typing import Dict, Any

from ..common import logger


class ProcessTaskManager:
    def __init__(self, task_queue: queue.Queue) -> None:
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._is_operation_in_progress = False
        self._task_queue = task_queue
        self._start_monitor_thread()  # Start the monitor thread
        self._start: bool = True

    def add(self, skip_obj: Any, task_id: str) -> None:
        """
        Add task control objects to the dictionary.
        :param skip_obj: An object that has a skip method.
        :param task_id: Task ID, used as the key in the dictionary.
        """
        if self._is_operation_in_progress:
            logger.warning("Cannot add task while another operation is in progress")
            return

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
        if self._is_operation_in_progress:
            logger.warning("Cannot remove task while another operation is in progress")
            return

        if task_id in self._tasks:
            del self._tasks[task_id]
            if not self._tasks:  # Check if the tasks dictionary is empty
                logger.info("No tasks remaining, stopping the monitor thread")
                self._start = False  # If tasks dictionary is empty, stop the loop
        else:
            logger.warning(f"No task found with task_id '{task_id}', operation invalid")

    def check(self, task_id: str) -> bool:
        """
        Check if the given task_id exists in the dictionary.

        :param task_id: Task ID.
        :return: True if the task_id exists, otherwise False.
        """
        return task_id in self._tasks

    def skip_task(self, task_id: str) -> None:
        """
        Skip the task based on task_id.

        :param task_id: Task ID.
        """
        self._is_operation_in_progress = True
        try:
            self._tasks[task_id]['skip'].skip()
        except Exception as error:
            logger.error(error)
        finally:
            self._is_operation_in_progress = False
            del self._tasks[task_id]

    def _start_monitor_thread(self) -> None:
        """
        Start a thread to monitor the task queue and inject exceptions into task threads if the task_id matches.
        """
        threading.Thread(target=self._monitor_task_queue, daemon=True).start()

    def _monitor_task_queue(self) -> None:
        while True:
            try:
                task_id = self._task_queue.get(timeout=1.0)

                if isinstance(task_id, tuple):
                    self._task_queue.put(task_id)
                    continue

                if task_id in self._tasks:
                    self._is_operation_in_progress = True
                    try:
                        self.skip_task(task_id)
                    except Exception as error:
                        logger.error(f"Error terminating task '{task_id}': {error}")
                    finally:
                        self._is_operation_in_progress = False
                        if not self._tasks:  # Check if the tasks dictionary is empty
                            logger.info("No tasks remaining, stopping the monitor thread")
                            break  # Stop the loop if tasks dictionary is empty
            except Exception:
                pass
            finally:
                if not self._start:
                    break
