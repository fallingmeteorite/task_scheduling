# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import gc
import queue
import threading
import time

from typing import Callable, List, Optional, Union

from ..common import logger, config
from ..mark import task_function_type
from ..manager import task_status_manager


class TaskScheduler:
    __slots__ = ['ban_task_names', 'core_task_queue', 'allocator_running', 'allocator_started', 'allocator_thread',
                 'timeout_check_interval', '_timeout_checker', '_task_event']

    def __init__(self) -> None:
        self.ban_task_names: List[str] = []
        self.core_task_queue: Optional[queue.Queue] = queue.Queue()
        self.allocator_running: bool = True
        self.allocator_started: bool = False
        self.allocator_thread: Optional[threading.Thread] = None
        self.timeout_check_interval: int = config["status_check_interval"]
        self._timeout_checker: Optional[threading.Timer] = None
        self._task_event = threading.Event()  # Add an event for task notification
        if self._timeout_checker is not None:
            self._start_timeout_checker()

    def add_task(self,
                 delay: Union[int, None],
                 daily_time: Union[int, None],
                 async_function: bool,
                 function_type: str,
                 timeout_processing: bool,
                 task_name: str, task_id: str,
                 func: Callable, priority: str, *args, **kwargs) -> bool:
        """
        Add a task to the scheduler.

        Args:
            delay: Delay time for timer tasks
            daily_time: Daily execution time for timer tasks
            async_function: Whether the function is asynchronous
            function_type: Type of function ("io", "cpu", "timer")
            timeout_processing: Whether timeout processing is enabled
            task_name: Name of the task
            task_id: Unique identifier for the task
            func: The function to execute
            priority: Task priority
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            bool: True if task was added successfully, False otherwise
        """
        # Check if the task name is in the ban list
        if task_name in self.ban_task_names:
            logger.warning(f"Task name '{task_name}' is banned, cannot add task, task ID: {task_id}")
            return False

        if function_type is None:
            function_type = task_function_type.read_from_dict(task_name)
            if function_type is None:
                logger.error(
                    f"Task name '{task_name}' has no function type, and no records are found in the cache file, tasks cannot be added!")
                return False

        self.core_task_queue.put((delay,
                                  daily_time,
                                  async_function,
                                  function_type,
                                  timeout_processing,
                                  task_name,
                                  task_id,
                                  func,
                                  priority,
                                  args,
                                  kwargs))

        self._task_event.set()  # Wake up the allocator thread
        task_status_manager.add_task_status(task_id, task_name, "queuing", None, None, None, timeout_processing, "NAN")

        if not self.allocator_started:
            self.allocator_started = True
            self.allocator_thread = threading.Thread(target=self._allocator, daemon=True)
            self.allocator_thread.start()

        return True

    def _allocator(self) -> None:
        from ..scheduler import add_api, cleanup_results_api
        threading.Thread(target=cleanup_results_api, daemon=True).start()
        while self.allocator_running:
            if not self.core_task_queue.empty():
                (delay, daily_time, async_function, function_type, timeout_processing, task_name, task_id, func,
                 priority,
                 args, kwargs) = self.core_task_queue.get()
                state = False

                if async_function:

                    if function_type == "io":
                        state = add_api("io_asyncio_task", None, None, timeout_processing, task_name, task_id, func,
                                        priority, *args, **kwargs)
                    if function_type == "cpu":
                        state = add_api("cpu_asyncio_task", None, None, timeout_processing, task_name, task_id, func,
                                        priority, *args, **kwargs)

                if not async_function:

                    if function_type == "io":
                        state = add_api("io_liner_task", None, None, timeout_processing, task_name, task_id, func,
                                        priority, *args, **kwargs)
                    if function_type == "cpu":
                        state = add_api("cpu_liner_task", None, None, timeout_processing, task_name, task_id, func,
                                        priority, *args, **kwargs)

                if function_type == "timer":

                    if not async_function:
                        state = add_api("timer_task", delay, daily_time, timeout_processing, task_name, task_id, func,
                                        priority, *args, **kwargs)
                    else:
                        logger.error("The timer function cannot be asynchronous code!")
                        state = "The timer function cannot be asynchronous code!"

                if state == False:
                    self.core_task_queue.put((delay,
                                              daily_time,
                                              async_function,
                                              function_type,
                                              timeout_processing,
                                              task_name,
                                              task_id,
                                              func,
                                              priority,
                                              args,
                                              kwargs))

                if not state == False and not state == True:
                    task_status_manager.add_task_status(task_id, None, "failed", None, None, state,
                                                        timeout_processing, state)
                try:
                    time.sleep(0.1)
                except KeyboardInterrupt:
                    pass

            else:
                self._task_event.clear()
                if self.core_task_queue.empty():
                    self._task_event.wait()  # Wait for the event to trigger

    def cancel_the_queue_task_by_name(self, task_name: str) -> None:
        """
        Cancel all queued tasks with the specified name.

        Args:
            task_name: The task name to be removed from the queue.
        """
        count = 0
        while count < len(self.core_task_queue.queue):
            item = self.core_task_queue.queue[count]
            if item[5] == task_name:
                self.core_task_queue.queue.remove(item)
                # Do not increase the count after deletion, because the next element will move to the current position.
            else:
                count += 1  # Only move to the next element if not deleting
        # Remove task status
        task_status_manager.remove_task_status(task_name)

        logger.warning("This type of name task has been removed")

    def add_ban_task_name(self, task_name: str) -> None:
        """
        Add a task name to the ban list.

        Args:
            task_name: The task name to be added to the ban list.
        """
        if task_name not in self.ban_task_names:
            self.ban_task_names.append(task_name)
            logger.info(f"Task name '{task_name}' has been added to the ban list.")
        else:
            logger.warning(f"Task name '{task_name}' is already in the ban list.")

    def remove_ban_task_name(self, task_name: str) -> None:
        """
        Remove a task name from the ban list.

        Args:
            task_name: The task name to be removed from the ban list.
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
        from ..scheduler import kill_api
        logger.info("Start checking the status of all tasks and fix them")
        current_time = time.time()
        for task_id, task_status in task_status_manager.task_status_dict.items():
            if task_status['status'] == "running" and task_status['is_timeout_enabled']:
                if current_time - task_status['start_time'] > config["watch_dog_time"]:
                    # Stop task
                    kill_api(task_id, task_status['task_type'])
        # Clean up unnecessary data along the way
        logger.warning(f"GC collected {gc.collect()} objects")
        self._start_timeout_checker()  # Restart the timer

    def _start_timeout_checker(self) -> None:
        """
        Start a timer that will periodically check for timeout tasks.
        """
        self._timeout_checker = threading.Timer(self.timeout_check_interval, self._check_timeouts)
        self._timeout_checker.daemon = True
        self._timeout_checker.start()

    def _stop_timeout_checker(self) -> None:
        """
        Stop the timeout checker timer if it is running.
        """
        if self._timeout_checker is not None:
            self._timeout_checker.cancel()
            self._timeout_checker = None

    def shutdown_scheduler(self, force_cleanup: bool) -> None:
        """
        Shutdown the scheduler, stop all tasks, and release resources.

        Args:
            force_cleanup: Force the end of running tasks
        """
        from ..scheduler import shutdown_api
        logger.info("Starting shutdown TaskScheduler.")

        # Clean up all resources in the task scheduler, stop running tasks, and empty the task queue.
        # Stop the task allocator
        self.allocator_running = False
        if self.allocator_thread and self.allocator_thread.is_alive():
            self.allocator_thread.join(timeout=0.1)

        # Stop the timeout checker
        self._stop_timeout_checker()

        # Clear the core task queue
        with self.core_task_queue.mutex:
            self.core_task_queue.queue.clear()

        # Turn off the scheduler
        shutdown_api(force_cleanup)

        logger.info("All scheduler has been shut down.")


task_scheduler = TaskScheduler()
