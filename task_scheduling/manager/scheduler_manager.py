# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Task scheduler module.

This module provides a comprehensive task scheduling system with support for
different task types, priority management, timeout handling, and thread-safe operations.
"""
import gc
import queue
import signal
import threading
import time
from typing import Callable, List, Optional, Union

from task_scheduling.common import logger
from task_scheduling.manager import task_status_manager


class TaskScheduler:
    """Main task scheduler for managing and distributing tasks.

    This scheduler handles task queuing, allocation to appropriate executors,
    timeout monitoring, and provides thread-safe task management operations.
    """
    __slots__ = ['ban_task_names', 'core_task_queue',
                 'allocator_running', 'allocator_started', 'allocator_thread',
                 '_task_event', '_lock', '_shutdown_lock',
                 '_allow_task_addition',
                 '_task_counter']

    def __init__(self) -> None:
        self.ban_task_names: List[str] = []
        self.core_task_queue: Optional[queue.Queue] = queue.Queue()
        self.allocator_running: bool = False
        self.allocator_started: bool = False
        self.allocator_thread: Optional[threading.Thread] = None
        self._task_event = threading.Event()  # Add an event for task notification
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._shutdown_lock = threading.Lock()  # Lock for shutdown operation
        self._allow_task_addition: bool = True
        self._task_counter: int = 0

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
        if not self._allow_task_addition:
            return False

        with self._lock:
            # Check if the task name is in the ban list
            if task_name in self.ban_task_names:
                logger.debug(f"Task name '{task_name}' is banned, cannot add task, task ID: {task_id}")
                return False

            if function_type is None:
                logger.warning(
                    f"Task name '{task_name}' has no function type, tasks cannot be added!")
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
            self._task_counter += 1
            if self._task_counter >= 40:
                logger.warning(f"Garbage collection performed. A total of <{gc.collect()}> objects were recycled.")

            self._task_event.set()  # Wake up the allocator thread
            task_status_manager.add_task_status(task_id, task_name, "queuing", None, None, None, timeout_processing,
                                                None)

            if not self.allocator_started:
                self.allocator_started = True
                self.allocator_running = True
                self.allocator_thread = threading.Thread(target=self._allocator, daemon=True)
                self.allocator_thread.start()

            return True

    def _allocator(self) -> None:
        # Avoid import issues
        from task_scheduling.scheduler import add_api, cleanup_results_api

        threading.Thread(target=cleanup_results_api, daemon=True).start()

        while self.allocator_running:
            if not self._allow_task_addition:
                time.sleep(0.1)
                continue

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
                        logger.warning("The timer function cannot be asynchronous code!")
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
                                                        timeout_processing, None)

            else:
                self._task_event.clear()
                if self.core_task_queue.empty():
                    self._task_event.wait()  # Wait for the event to trigger

    def _stop_task_addition(self) -> None:
        """
        Stop task addition by banning all task names
        """
        self._allow_task_addition = False
        logger.warning(f"Task addition was disabled by user!")

    def _resume_task_addition(self) -> None:
        """
        Resume task addition by removing all bans
        """
        self._allow_task_addition = True
        logger.warning(f"Task addition was enabled by user!")

    def cancel_the_queue_task_by_name(self, task_name: str) -> None:
        """
        Cancel all queued tasks with the specified name.

        Args:
            task_name: The task name to be removed from the queue.
        """
        with self._lock:
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
        with self._lock:
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
        with self._lock:
            if task_name in self.ban_task_names:
                self.ban_task_names.remove(task_name)
                logger.info(f"Task name '{task_name}' has been removed from the ban list.")
            else:
                logger.warning(f"Task name '{task_name}' is not in the ban list.")

    def shutdown_scheduler(self, signum=None, frame=None) -> None:
        """
        Shutdown the scheduler, stop all tasks, and release resources.
        """
        with self._shutdown_lock:
            # Avoid import issues
            from task_scheduling.scheduler import shutdown_api
            logger.info("Starting shutdown TaskScheduler.")
            self._stop_task_addition()

            # Clean up all resources in the task scheduler, stop running tasks, and empty the task queue.
            # Stop the task allocator
            with self._lock:
                self.allocator_running = False
                self._task_event.set()  # Wake up allocator thread to exit

            if self.allocator_thread and self.allocator_thread.is_alive():
                self.allocator_thread.join(timeout=1.0)

            # Clear the core task queue
            with self._lock:
                with self.core_task_queue.mutex:
                    self.core_task_queue.queue.clear()

                # Reset status
                self.ban_task_names.clear()
                self.allocator_started = False
                self.allocator_thread = None

            # Turn off the scheduler
            shutdown_api()

            # Clear task status
            task_status_manager.details_manager_shutdown()

            logger.info("All scheduler has been shut down.")
            # Restore default settings
            self._allow_task_addition = True

            if signum and frame:
                # Restore the default handler and resend the signal
                logger.error("Abnormal exit, resource cleanup completed!")
                signal.signal(signum, signal.SIG_DFL)
                signal.raise_signal(signum)


task_scheduler = TaskScheduler()
