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

    def add(self, terminate_obj: Any, pause_ctx: Any, task_id: str) -> None:
        """
        Add task control objects to the dictionary.
        :param terminate_obj: An object that has a terminate method.
          :param pause_ctx: An object that has a pause method.
        :param task_id: Task ID, used as the key in the dictionary.
        """
        with self._operation_lock:  # Lock for thread-safe dictionary access
            if task_id in self._tasks:
                logger.warning(f"Task with task_id '{task_id}' already exists, overwriting")
            self._tasks[task_id] = {
                'terminate': terminate_obj,
                'pause': pause_ctx
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
                    logger.debug(f"Worker {os.getpid()} no tasks remaining, stopping the monitor thread")
                    self._start = False  # If tasks dictionary is empty, stop the loop

    def check(self, task_id: str) -> bool:
        """
        Check if the given task_id exists in the dictionary.
        :param task_id: Task ID.
        :return: True if the task_id exists, otherwise False.
        """
        with self._operation_lock:  # Lock for thread-safe dictionary access
            return task_id in self._tasks

    def terminate_task(self, task_id: str) -> None:
        """
        Terminate the task based on task_id.
        :param task_id: Task ID.
        """
        with self._operation_lock:  # Lock for thread-safe dictionary access
            if task_id in self._tasks:
                try:
                    self._tasks[task_id]['terminate'].terminate()  # Perform the terminate operation outside the lock
                except Exception as error:
                    logger.error(f"Error terminating task '{task_id}': {error}")

            else:
                logger.warning(f"No task found with task_id '{task_id}', operation invalid")

    def pause_task(self, task_id: str) -> None:
        """
        Pause the task based on task_id.
        :param task_id: Task ID.
        """
        with self._operation_lock:  # Lock for thread-safe dictionary access
            if task_id in self._tasks:
                try:
                    self._tasks[task_id]['pause'].pause()
                except Exception as error:
                    logger.error(error)

            else:
                logger.warning(f"No task found with task_id '{task_id}', operation invalid")

    def resume_task(self, task_id: str) -> None:
        """
        Resume the task based on task_id.

        :param task_id: Task ID.
        """
        with self._operation_lock:  # Lock for thread-safe dictionary access
            if task_id in self._tasks:
                try:
                    self._tasks[task_id]['pause'].resume()
                except Exception as error:
                    logger.error(error)
                del self._tasks[task_id]
            else:
                logger.warning(f"No task found with task_id '{task_id}', operation invalid")

    def _start_monitor_thread(self) -> None:
        """
        Start a thread to monitor the task queue and inject exceptions into task threads if the task_id matches.
        """
        threading.Thread(target=self._monitor_task_queue, daemon=True).start()

    def _monitor_task_queue(self) -> None:
        while self._start:
            try:
                task_id, target = self._task_queue.get(timeout=0.1)

                if self.check(task_id):  # Check if the task_id exists in the dictionary
                    if target == "kill":
                        self.terminate_task(task_id)  # Terminate the task if it exists
                    if target == "pause":
                        self.pause_task(task_id)  # Pause the task if it exists
                    if target == "resume":
                        self.resume_task(task_id)  # Resume the task if it exists

                    with self._operation_lock:  # Lock for thread-safe dictionary access
                        if not self._tasks:  # Check if the tasks dictionary is empty
                            logger.debug(f"Worker {os.getpid()} no tasks remaining, stopping the monitor thread")
                            break  # Stop the loop if tasks dictionary is empty

                else:
                    self._task_queue.put((task_id, target))
            except queue.Empty:
                pass  # Ignore empty queue exceptions
            except Exception as error:
                logger.error(f"Error in monitor thread: {error}")
            finally:
                time.sleep(0.1)
