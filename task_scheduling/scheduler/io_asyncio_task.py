# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import asyncio
import queue
import threading
import time
from typing import Dict, Tuple, Callable, Optional, Any

from ..common import logger
from ..config import config
from ..manager import task_status_manager
from ..stopit import ThreadTaskManager

# Create Manager instance
_task_manager = ThreadTaskManager()


class IoAsyncTask:
    """
    Asynchronous task manager class, responsible for scheduling, executing, and monitoring asynchronous tasks.
    """
    __slots__ = [
        '_task_queues', '_running_tasks',
        '_condition', '_scheduler_lock',
        '_scheduler_started', '_scheduler_stop_event', '_scheduler_threads',
        '_event_loops',
        '_idle_timers', '_idle_timeout', '_idle_timer_lock',
        '_task_results', '_task_counters'
    ]

    def __init__(self) -> None:
        """
        Initialize the asynchronous task manager.
        """
        self._task_queues: Dict[str, queue.Queue] = {}  # Task queues for each task name
        self._running_tasks: Dict[str, list[Any]] = {}  # Running tasks

        self._condition = threading.Condition()  # Condition variable for thread synchronization
        self._scheduler_lock = threading.RLock()  # Reentrant lock for scheduler operations

        self._scheduler_started = False  # Whether the scheduler thread has started
        self._scheduler_stop_event = threading.Event()  # Scheduler thread stop event
        self._scheduler_threads: Dict[str, threading.Thread] = {}  # Scheduler threads for each task name

        self._event_loops: Dict[str, Any] = {}  # Event loops for each task name

        self._idle_timers: Dict[str, threading.Timer] = {}  # Idle timers for each task name
        self._idle_timeout = config["max_idle_time"]  # Idle timeout, default is 60 seconds
        self._idle_timer_lock = threading.Lock()  # Idle timer lock

        self._task_results: Dict[str, Any] = {}  # Store task return results, keep up to 2 results for each task ID
        self._task_counters: Dict[str, int] = {}  # Used to track the number of tasks being executed in each event loop

    # Add the task to the scheduler
    def add_task(self,
                 timeout_processing: bool,
                 task_name: str,
                 task_id: str,
                 func: Callable,
                 *args,
                 **kwargs) -> bool:
        """
        Add a task to the task queue.

        Args:
            timeout_processing (bool): Whether to enable timeout processing.
            task_name (str): Task name (can be repeated).
            task_id (str): Task ID (must be unique).
            func (Callable): Task function.
            *args: Positional arguments for the task function.
            **kwargs: Keyword arguments for the task function.

        Returns:
            bool: Whether the task was successfully added.
        """
        try:
            with self._scheduler_lock:
                if task_name not in self._task_queues:
                    self._task_queues[task_name] = queue.Queue()

                if self._task_queues[task_name].qsize() >= config["io_asyncio_task"]:
                    logger.warning(f"Io asyncio task | {task_id} | not added, queue is full")
                    return False

                task_status_manager.add_task_status(task_id, None, "waiting", None, None, None, None)

                self._task_queues[task_name].put((timeout_processing, task_name, task_id, func, args, kwargs))

                # If the scheduler thread has not started, start it
                if task_name not in self._scheduler_threads or not self._scheduler_threads[task_name].is_alive():
                    self._event_loops[task_name] = asyncio.new_event_loop()
                    self._task_counters[task_name] = 0  # Initialize the task counter
                    self._start_scheduler(task_name)

                # Cancel the idle timer
                self._cancel_idle_timer(task_name)

                with self._condition:
                    self._condition.notify()  # Notify the scheduler thread that a new task is available

                return True
        except Exception as e:
            logger.error(f"Error adding task | {task_id} |: {e}")
            return False

    # Start the scheduler
    def _start_scheduler(self,
                         task_name: str) -> None:
        """
        Start the scheduler thread and the event loop thread for a specific task name.

        Args:
            task_name (str): Task name.
        """
        with self._condition:
            if task_name not in self._scheduler_threads or not self._scheduler_threads[task_name].is_alive():
                self._scheduler_started = True
                self._scheduler_threads[task_name] = threading.Thread(target=self._scheduler, args=(task_name,),
                                                                      daemon=True)
                self._scheduler_threads[task_name].start()

                # Start the event loop thread
                threading.Thread(target=self._run_event_loop, args=(task_name,), daemon=True).start()

    # Stop the scheduler
    def _stop_scheduler(self,
                        task_name: str) -> None:
        """
        Stop the scheduler and event loop for a specific task name.

        Args:
            task_name (str): Task name.
        """
        with self._scheduler_lock:
            # Check if all tasks are completed
            if not self._task_queues[task_name].empty() or len(self._running_tasks) != 0:
                logger.warning(f"Io asyncio task was detected to be running, and the task stopped terminating")
                return None

            self._scheduler_stop_event.set()

            with self._condition:
                self._scheduler_started = False
                self._condition.notify_all()

            # Clear the task queue
            self._clear_task_queue(task_name)

            # Stop the event loop
            self._stop_event_loop(task_name)

            # Wait for the scheduler thread to finish
            self._join_scheduler_thread(task_name)

            # Reset parameters for scheduler restart
            if task_name in self._event_loops:
                del self._event_loops[task_name]
            if task_name in self._scheduler_threads:
                del self._scheduler_threads[task_name]
            if task_name in self._task_queues:
                del self._task_queues[task_name]
            if task_name in self._idle_timers:
                del self._idle_timers[task_name]
            if task_name in self._task_counters:
                del self._task_counters[task_name]

            logger.info(
                f"Scheduler and event loop for task | {task_name} | have stopped, all resources have been released and parameters reset")

    def stop_all_schedulers(self,
                            force_cleanup: bool,
                            system_operations: bool = False) -> None:
        """
        Stop all schedulers and event loops, and forcibly kill all tasks if force_cleanup is True.

        Args:
            force_cleanup (bool): Force the end of all running tasks.
            system_operations (bool): System execution metrics.
        """
        with self._scheduler_lock:
            # Check if all tasks are completed
            if not all(q.empty() for q in self._task_queues.values()) or len(self._running_tasks) != 0:
                if system_operations:
                    logger.warning(f"Io asyncio task was detected to be running, and the task stopped terminating")
                    return None

            if force_cleanup:
                logger.warning("Force stopping all schedulers and cleaning up tasks")
                # Forcibly cancel all running tasks
                _task_manager.cancel_all_tasks()
                self._scheduler_stop_event.set()
            else:
                self._scheduler_stop_event.set()

            with self._condition:
                self._scheduler_started = False
                self._condition.notify_all()

            # Clear all task queues
            for task_name in list(self._task_queues.keys()):
                self._clear_task_queue(task_name)

            # Stop all event loops
            for task_name in list(self._event_loops.keys()):
                self._stop_event_loop(task_name)

            # Wait for all scheduler threads to finish
            for task_name in list(self._scheduler_threads.keys()):
                self._join_scheduler_thread(task_name)

            # Clean up all task return results
            with self._condition:
                self._task_results.clear()

            # Reset parameters for scheduler restart
            self._event_loops.clear()
            self._scheduler_threads.clear()
            self._task_queues.clear()
            self._idle_timers.clear()
            self._task_counters.clear()

    # Task scheduler
    def _scheduler(self,
                   task_name: str) -> None:
        """
        Scheduler function, fetch tasks from the task queue and submit them to the event loop for execution.

        Args:
            task_name (str): Task name.
        """
        asyncio.set_event_loop(self._event_loops[task_name])

        while not self._scheduler_stop_event.is_set():
            with self._condition:
                while (self._task_queues[task_name].empty() or self._task_counters[
                    task_name] >= config["io_asyncio_task"]) and not self._scheduler_stop_event.is_set():
                    self._condition.wait()

                if self._scheduler_stop_event.is_set():
                    break

                if self._task_queues[task_name].qsize() == 0:
                    continue

                task = self._task_queues[task_name].get()

            # Execute the task after the lock is released
            timeout_processing, task_name, task_id, func, args, kwargs = task
            future = asyncio.run_coroutine_threadsafe(self._execute_task(task), self._event_loops[task_name])
            _task_manager.add(future, None, task_id)
            with self._condition:
                self._running_tasks[task_id] = [future, task_name]
                self._task_counters[task_name] += 1

    # A function that executes a task
    async def _execute_task(self,
                            task: Tuple[bool, str, str, Callable, Tuple, Dict]) -> Any:
        """
        Execute an asynchronous task.

        Args:
            task (Tuple[bool, str, str, Callable, Tuple, Dict]): Tuple containing task details.
                - timeout_processing (bool): Whether timeout processing is enabled.
                - task_name (str): Name of the task.
                - task_id (str): ID of the task.
                - func (Callable): The function to execute.
                - args (Tuple): Arguments to pass to the function.
                - kwargs (Dict): Keyword arguments to pass to the function.

        Returns:
            Any: Result of the task execution or error message.
        """
        # Unpack task tuple into local variables
        timeout_processing, task_name, task_id, func, args, kwargs = task
        return_results = None
        try:
            # Modify the task status
            task_status_manager.add_task_status(task_id, None, "running", time.time(), None, None, None)

            logger.info(f"Start running io asyncio task | {task_id} | ")

            # If the task needs timeout processing, set the timeout time
            if timeout_processing:
                return_results = await asyncio.wait_for(func(*args, **kwargs),
                                                        timeout=config["watch_dog_time"])
            else:
                return_results = await func(*args, **kwargs)

            # Update task status to "completed"
            task_status_manager.add_task_status(task_id, None, "completed", None, time.time(), None, None)

        except asyncio.TimeoutError:
            logger.warning(f"Io asyncio task | {task_id} | timed out, forced termination")
            task_status_manager.add_task_status(task_id, None, "timeout", None, None, None, None)
            return_results = "error happened"
        except asyncio.CancelledError:
            logger.warning(f"Io asyncio task | {task_id} | was cancelled")
            task_status_manager.add_task_status(task_id, None, "cancelled", None, None, None,
                                                None)
            return_results = "error happened"
        except Exception as e:
            logger.error(f"Io asyncio task | {task_id} | execution failed: {e}")
            task_status_manager.add_task_status(task_id, None, "failed", None, None, e, None)
            return_results = "error happened"
        finally:
            if return_results == "error happened":
                _task_manager.remove(task_id)

            # Opt-out will result in the deletion of the information and the following processing will not be possible
            with self._condition:
                # Save the result returned by the task, and keep only one result
                if return_results is not None:
                    if return_results != "error happened":
                        self._task_results[task_id] = return_results

                # Remove the task from running tasks dictionary
                if task_id in self._running_tasks:
                    del self._running_tasks[task_id]

                # Queue task counters (ensure it doesn't go below 0)
                if task_name in self._task_counters and self._task_counters[task_name] > 0:
                    self._task_counters[task_name] -= 1

                # Check if all tasks are completed
                if self._task_queues.get(task_name) is not None:
                    if self._task_queues[task_name].empty() and len(self._running_tasks) == 0:
                        self._reset_idle_timer(task_name)

                # Notify the scheduler to continue scheduling new tasks
                self._condition.notify()

    # The task scheduler closes the countdown
    def _reset_idle_timer(self,
                          task_name: str) -> None:
        """
        Reset the idle timer for a specific task name.

        Args:
            task_name (str): Task name.
        """
        with self._idle_timer_lock:
            if task_name in self._idle_timers and self._idle_timers[task_name] is not None:
                self._idle_timers[task_name].cancel()
            self._idle_timers[task_name] = threading.Timer(self._idle_timeout, self._stop_scheduler,
                                                           args=(task_name,))
            self._idle_timers[task_name].start()

    def _cancel_idle_timer(self,
                           task_name: str) -> None:
        """
        Cancel the idle timer for a specific task name.

        Args:
            task_name (str): Task name.
        """
        with self._idle_timer_lock:
            if task_name in self._idle_timers and self._idle_timers[task_name] is not None:
                self._idle_timers[task_name].cancel()
                del self._idle_timers[task_name]

    def _clear_task_queue(self,
                          task_name: str) -> None:
        """
        Clear the task queue for a specific task name.

        Args:
            task_name (str): Task name.
        """
        while not self._task_queues[task_name].empty():
            self._task_queues[task_name].get(timeout=1)

    def _join_scheduler_thread(self,
                               task_name: str) -> None:
        """
        Wait for the scheduler thread to finish for a specific task name.

        Args:
            task_name (str): Task name.
        """
        if task_name in self._scheduler_threads and self._scheduler_threads[task_name].is_alive():
            self._scheduler_threads[task_name].join()

    def force_stop_task(self,
                        task_id: str) -> bool:
        """
        Force stop a task by its task ID.

        Args:
            task_id (str): Task ID.

        Returns:
            bool: Whether the task was successfully force stopped.
        """
        # Read operation, no need to hold a lock
        if not _task_manager.check(task_id):
            logger.warning(f"Io asyncio task | {task_id} | does not exist or is already completed")
            return False

        _task_manager.cancel_task(task_id)
        with self._condition:
            if task_id in self._task_results:
                del self._task_results[task_id]
        return True

    # Obtain the information returned by the corresponding task
    def get_task_result(self,
                        task_id: str) -> Optional[Any]:
        """
        Get the result of a task. If there is a result, return and delete the oldest result; if no result, return None.

        Args:
            task_id (str): Task ID.

        Returns:
            Optional[Any]: Task return result, or None if the task is not completed or does not exist.
        """
        if task_id in self._task_results:
            result = self._task_results[task_id]
            del self._task_results[task_id]  # Delete the results
            return result
        return None

    def _run_event_loop(self,
                        task_name: str) -> None:
        """
        Run the event loop for a specific task name.

        Args:
            task_name (str): Task name.
        """
        asyncio.set_event_loop(self._event_loops[task_name])
        self._event_loops[task_name].run_forever()

    def _stop_event_loop(self,
                         task_name: str) -> None:
        """
        Stop the event loop for a specific task name.

        Args:
            task_name (str): Task name.
        """
        if task_name in self._event_loops and self._event_loops[
            task_name].is_running():  # Ensure the event loop is running
            try:
                self._event_loops[task_name].call_soon_threadsafe(self._event_loops[task_name].stop)
                # Wait for the event loop thread to finish
                if task_name in self._scheduler_threads and self._scheduler_threads[task_name].is_alive():
                    self._scheduler_threads[task_name].join(timeout=1)  # Wait up to 1 second
            except Exception as e:
                logger.error(f"Io asyncio task | stopping event loop | error occurred: {e}")
