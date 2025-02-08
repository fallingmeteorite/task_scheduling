import queue
import threading
import time
from typing import Callable, List, Tuple, Optional

from .common import logger
from .config import config
from .manager import task_status_manager
from .scheduler import io_async_task, io_liner_task, cpu_liner_task, cpu_async_task, timer_task


def is_banana(item: Tuple, task_name: str) -> bool:
    return item[1] == task_name


class TaskScheduler:
    __slots__ = ['ban_task_names', 'core_task_queue', 'allocator_running', 'allocator_started', 'allocator_thread',
                 'timeout_check_interval',
                 '_timeout_checker']

    def __init__(self):
        self.ban_task_names: List[str] = []
        self.core_task_queue: Optional[queue.Queue] = queue.Queue()
        self.allocator_running: bool = True
        self.allocator_started: bool = False
        self.allocator_thread: Optional[threading.Thread] = None
        self.timeout_check_interval: int = config["status_check_interval"]
        self._timeout_checker: Optional[threading.Timer]

    def add_task(self, async_function: bool, function_type: str, timeout_processing: bool, task_name: str, task_id: str,
                 func: Callable, *args, **kwargs):
        # Check if the task name is in the ban list
        if task_name in self.ban_task_names:
            logger.warning(f"Task name '{task_name}' is banned, cannot add task.")
            return None

        self.core_task_queue.put(
            (async_function, function_type, timeout_processing, task_name, task_id, func, args, kwargs))

        if not self.allocator_started:
            self.allocator_started = True
            self.allocator_thread = threading.Thread(target=self._allocator, daemon=True)
            self.allocator_thread.start()

    def _allocator(self):
        while self.allocator_running:
            if not self.core_task_queue.empty():
                async_function, function_type, timeout_processing, task_name, task_id, func, args, kwargs = self.core_task_queue.get()
                state = False
                if async_function:
                    if function_type == "io":
                        state = io_async_task.add_task(timeout_processing, task_name, task_id, func, *args, **kwargs)
                    if function_type == "cpu":
                        state = cpu_async_task.add_task(timeout_processing, task_name, task_id, func, *args, **kwargs)

                if not async_function:
                    if function_type == "io":
                        state = io_liner_task.add_task(timeout_processing, task_name, task_id, func, *args, **kwargs)
                    if function_type == "cpu":
                        state = cpu_liner_task.add_task(timeout_processing, task_name, task_id, func, *args, **kwargs)

                if not state:
                    self.core_task_queue.put(
                        (async_function, function_type, timeout_processing, task_name, task_id, func, args, kwargs))

            else:
                time.sleep(0.1)

    def cancel_the_queue_task_by_name(self, task_name: str) -> None:

        for item in self.core_task_queue.queue:
            if is_banana(item, task_name):
                self.core_task_queue.queue.remove(item)

    def add_ban_task_name(self, task_name: str) -> None:
        """
        Add a task name to the ban list.

        :param task_name: The task name to be added to the ban list.
        """
        if task_name not in self.ban_task_names:
            self.ban_task_names.append(task_name)
            logger.info(f"Task name '{task_name}' has been added to the ban list.")
        else:
            logger.warning(f"Task name '{task_name}' is already in the ban list.")

    def remove_ban_task_name(self, task_name: str) -> None:
        """
        Remove a task name from the ban list.

        :param task_name: The task name to be removed from the ban list.
        """
        if task_name in self.ban_task_names:
            self.ban_task_names.remove(task_name)
            logger.info(f"Task name '{task_name}' has been removed from the ban list.")
        else:
            logger.warning(f"Task name '{task_name}' is not in the ban list.")

    def _check_timeouts(self) -> None:
        """
        Check for tasks that have exceeded their timeout time based on task start times.
        """
        current_time = time.time()
        for task_id, task_status in task_status_manager.task_status_dict.items():
            if task_status['status'] == "running" and task_status['is_timeout_enabled']:
                if current_time - task_status['start_time'] > config["watch_dog_time"]:
                    # Stop task
                    io_async_task.force_stop_task(task_id)
                    io_liner_task.force_stop_task(task_id)
                    timer_task.force_stop_task(task_id)
                    cpu_liner_task.force_stop_task(task_id)
                    cpu_async_task.force_stop_task(task_id)
        self._start_timeout_checker()  # Restart the timer

    def _start_timeout_checker(self):
        """
        Start a timer that will periodically check for timeout tasks.
        """
        self._timeout_checker = threading.Timer(self.timeout_check_interval, self._check_timeouts)
        self._timeout_checker.start()

    def _stop_timeout_checker(self):
        """
        Stop the timeout checker timer if it is running.
        """
        if self._timeout_checker is not None:
            self._timeout_checker.cancel()
            self._timeout_checker = None


task_scheduler = TaskScheduler()


def shutdown(force_cleanup: bool) -> None:
    """
    :param force_cleanup: Force the end of a running task

    Shutdown the scheduler, stop all tasks, and release resources.
    Only checks if the scheduler is running and forces a shutdown if necessary.
    """
    # Shutdown asynchronous task scheduler if running
    if hasattr(timer_task, "scheduler_started") and timer_task.scheduler_started:
        logger.info("Detected Cpu linear task scheduler is running, shutting down...")
        timer_task.stop_scheduler(force_cleanup)
        logger.info("Cpu linear task scheduler has been shut down.")

    # Shutdown asynchronous task scheduler if running
    if hasattr(cpu_liner_task, "scheduler_started") and cpu_liner_task.scheduler_started:
        logger.info("Detected Cpu linear task scheduler is running, shutting down...")
        cpu_liner_task.stop_scheduler(force_cleanup)
        logger.info("Cpu linear task scheduler has been shut down.")

    # Shutdown asynchronous task scheduler if running
    if hasattr(io_async_task, "scheduler_started") and io_async_task.scheduler_started:
        logger.info("Detected io asyncio task scheduler is running, shutting down...")
        io_async_task.stop_all_schedulers(force_cleanup)
        logger.info("Io asyncio task scheduler has been shut down.")

    # Shutdown linear task scheduler if running
    if hasattr(io_liner_task, "scheduler_started") and io_liner_task.scheduler_started:
        logger.info("Detected io linear task scheduler is running, shutting down...")
        io_liner_task.stop_scheduler(force_cleanup)
        logger.info("Io linear task scheduler has been shut down.")

    logger.info("All scheduler has been shut down.")
