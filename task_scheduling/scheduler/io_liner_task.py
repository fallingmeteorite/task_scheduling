# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""IO-bound linear task execution module.

This module provides a task scheduler for IO-bound linear tasks using
thread pool execution with priority-based scheduling and timeout handling.
"""
import queue
import threading
import math
import time
import platform

from concurrent.futures import ThreadPoolExecutor, Future
from functools import partial
from typing import Callable, Dict, Tuple, Optional, Any, List

from ..common import logger, config
from ..manager import task_status_manager
from ..control import ThreadTaskManager
from ..handling import TimeoutException, ThreadSuspender, StopException, ThreadingTimeout, ThreadTerminator
from .utils import TaskCounter, retry_on_error_decorator_check

# Create Manager instance
_task_counter = TaskCounter("io_liner_task")
_task_manager = ThreadTaskManager()
_threadsuspender = ThreadSuspender()
_threadterminator = ThreadTerminator()


def _execute_task(task: Tuple[bool, str, str, Callable, str, Tuple, Dict]) -> Any:
    """
    Execute a task and handle its status.

    Args:
        task: A tuple containing task details.
            - timeout_processing: Whether timeout processing is enabled.
            - task_name: Name of the task.
            - task_id: ID of the task.
            - func: The function to execute.
            - priority: Task priority.
            - args: Arguments to pass to the function.
            - kwargs: Keyword arguments to pass to the function.

    Returns:
        Result of the task execution or error message.
    """
    timeout_processing, task_name, task_id, func, priority, args, kwargs = task
    logger.debug(f"Start running task, task ID: {task_id}")
    try:
        with _threadterminator.terminate_control() as terminate_ctx:
            with _threadsuspender.suspend_context() as pause_ctx:

                _task_manager.add(None, terminate_ctx, pause_ctx, task_id)

                task_status_manager.add_task_status(task_id, None, "running", time.time(), None, None, None, None)

                if timeout_processing:
                    with ThreadingTimeout(seconds=config["watch_dog_time"], swallow_exc=False):
                        if retry_on_error_decorator_check(func):
                            result = func(task_id, *args, **kwargs)
                        else:
                            result = func(*args, **kwargs)
                else:
                    if retry_on_error_decorator_check(func):
                        result = func(task_id, *args, **kwargs)
                    else:
                        result = func(*args, **kwargs)

        _task_manager.remove(task_id)
    except TimeoutException:
        logger.warning(f"task | {task_id} | timed out, forced termination")
        task_status_manager.add_task_status(task_id, None, "timeout", None, None, None, None, None)

        result = "timeout action"
    except StopException:
        logger.warning(f"task | {task_id} | was cancelled")
        task_status_manager.add_task_status(task_id, None, "cancelled", None, None, None, None, None)

        result = "cancelled action"
    except Exception as error:
        if config["exception_thrown"]:
            raise

        logger.error(f"task | {task_id} | execution failed: {error}")
        task_status_manager.add_task_status(task_id, None, "failed", None, None, error, None, None)

        result = "failed action"

    finally:
        if _task_manager.exists(task_id):
            _task_manager.remove(task_id)

    return result


class IoLinerTask:
    """
    Linear task manager class, responsible for managing the scheduling, execution, and monitoring of linear tasks.
    """
    __slots__ = [
        '_task_queue', '_running_tasks',
        '_lock', '_condition', '_scheduler_lock',
        '_scheduler_started', '_scheduler_stop_event', '_scheduler_thread',
        '_idle_timer', '_idle_timeout', '_idle_timer_lock',
        '_task_results',
        '_executor'
    ]

    def __init__(self) -> None:
        """
        Initialize the IoLinerTask manager.
        """

        self._task_queue = queue.Queue()  # Task queue
        self._running_tasks = {}  # Running tasks

        self._lock = threading.Lock()  # Lock to protect access to shared resources
        self._scheduler_lock = threading.RLock()  # Reentrant lock for scheduler operations
        self._condition = threading.Condition(self._lock)  # Condition variable using existing lock

        self._scheduler_started = False  # Whether the scheduler thread has started
        self._scheduler_stop_event = threading.Event()  # Scheduler thread stop event
        self._scheduler_thread: Optional[threading.Thread] = None  # Scheduler thread

        self._idle_timer: Optional[threading.Timer] = None  # Idle timer
        self._idle_timeout = config["max_idle_time"]  # Idle timeout, default is 60 seconds
        self._idle_timer_lock = threading.Lock()  # Idle timer lock

        self._task_results: Dict[str, List[Any]] = {}  # Store task return results

        self._executor: Optional[ThreadPoolExecutor] = None

    # Add the task to the scheduler
    def add_task(self,
                 timeout_processing: bool,
                 task_name: str,
                 task_id: str,
                 func: Callable,
                 priority: str,
                 *args,
                 **kwargs) -> Any:
        """
        Add a task to the task queue.

        Args:
            timeout_processing: Whether to enable timeout processing.
            task_name: Task name (can be repeated).
            task_id: Task ID (must be unique).
            func: Task function.
            priority: Mission importance level.
            *args: Positional arguments for the task function.
            **kwargs: Keyword arguments for the task function.

        Returns:
            Whether the task was successfully added.
        """
        try:
            with self._scheduler_lock:
                # Use a lock to protect queue size checks and task execution checks
                with self._lock:
                    if not _task_counter.is_high_priority(priority):
                        # Atomic Check Queue Size and Running Tasks
                        queue_size = self._task_queue.qsize()
                        running_task_names = {details[1] for details in self._running_tasks.values()}

                        if queue_size >= config["io_liner_task"]:
                            return False

                        if task_name in running_task_names:
                            return False
                    else:
                        if not _task_counter.add_count(math.ceil(config["io_liner_task"])):
                            return False

                if self._scheduler_stop_event.is_set() and not self._scheduler_started:
                    self._join_scheduler_thread()

                # Reduce the granularity of the lock
                task_status_manager.add_task_status(task_id, None, "waiting", None, None, None, None, "io_liner_task")

                self._task_queue.put((timeout_processing, task_name, task_id, func, priority, args, kwargs))

                if not self._scheduler_started:
                    self._start_scheduler()

                with self._condition:
                    self._condition.notify()

                self._cancel_idle_timer()

                return True
        except Exception as error:
            return error

    # Start the scheduler
    def _start_scheduler(self) -> None:
        """
        Start the scheduler thread.
        """
        self._scheduler_started = True
        self._scheduler_stop_event.clear()
        self._scheduler_thread = threading.Thread(target=self._scheduler, daemon=True)
        self._scheduler_thread.start()

    # Stop the scheduler
    def stop_scheduler(self,
                       system_operations: bool = False) -> None:
        """
        Stop the scheduler thread.

        Args:
            system_operations: System execution metrics.
        """
        # Turn off the scheduler
        self._scheduler_stop_event.set()

        # First notify all waiting threads
        with self._condition:
            self._condition.notify_all()

        with self._scheduler_lock:
            # Check if all tasks are completed
            if system_operations:
                with self._lock:
                    if not self._task_queue.empty() or len(self._running_tasks) != 0:
                        logger.warning(f"task was detected to be running, and the task stopped terminating")
                        return None

            # Terminate the task
            _task_manager.terminate_all_tasks()

            # Ensure the executor is properly shut down
            if self._executor:
                # Use wait=True to ensure a safe shutdown
                self._executor.shutdown(wait=False, cancel_futures=True)

            # Clear the task queue - Needs to be protected by a lock
            self._clear_task_queue()

            # Wait for the scheduler thread to finish
            self._join_scheduler_thread()

            self._wait_tasks_end()
            # Reset state variables - Needs to be protected by a lock
            with self._lock:
                self._scheduler_started = False
                self._running_tasks.clear()
                self._task_results.clear()

            self._scheduler_thread = None

            # Cancel idle timer
            with self._idle_timer_lock:
                if self._idle_timer is not None:
                    self._idle_timer.cancel()
                    self._idle_timer = None

            logger.debug(
                "Scheduler and event loop have stopped, all resources have been released and parameters reset")
        return None

    def _wait_tasks_end(self) -> None:
        """
        Wait for all tasks to finish
        """
        while True:
            if len(self._running_tasks) == 0:
                break
            time.sleep(0.01)

    # Task scheduler
    def _scheduler(self) -> None:
        """
        Scheduler function, fetch tasks from the task queue and submit them to the thread pool for execution.
        """
        with ThreadPoolExecutor(max_workers=int(config["io_liner_task"] + math.ceil(config["io_liner_task"] / 2))
                                ) as executor:
            self._executor = executor
            while not self._scheduler_stop_event.is_set():
                with self._condition:
                    # Use loops and timeouts to prevent spurious wakeup
                    while (self._task_queue.empty() and
                           not self._scheduler_stop_event.is_set()):
                        self._condition.wait(timeout=1.0)  # Add a timeout to prevent waiting indefinitely

                    if self._scheduler_stop_event.is_set():
                        break

                    # Check the queue status again, as it may have been falsely awakened or timed out.
                    if self._task_queue.empty():
                        continue

                    task = self._task_queue.get()

                timeout_processing, task_name, task_id, func, priority, args, kwargs = task

                # Use a lock to protect updates to the task dictionary during execution
                with self._lock:
                    future = executor.submit(_execute_task, task)
                    self._running_tasks[task_id] = [future, task_name, priority]

                    future.add_done_callback(partial(self._task_done, task_id))

    # A function that executes a task
    def _task_done(self,
                   task_id: str,
                   future: Future) -> None:
        """
        Callback function after a task is completed.

        Args:
            task_id: Task ID.
            future: Future object corresponding to the task.
        """
        result = None
        try:
            result = future.result()  # Get task result, exceptions will be raised here
        except StopException:
            logger.warning(f"task | {task_id} | was cancelled")
            task_status_manager.add_task_status(task_id, None, "cancelled", None, None, None, None, None)
            result = "cancelled action"
        except Exception:
            # Other exceptions have already been handled in _execute_task.
            result = "failed action"
        finally:
            # Store task return results - Use a lock to protect the result dictionary
            with self._lock:
                if result not in ["timeout action", "cancelled action", "failed action"]:
                    if result is not None:
                        self._task_results[task_id] = [result, time.time()]
                    else:
                        self._task_results[task_id] = ["completed action", time.time()]
                else:
                    self._task_results[task_id] = [result, time.time()]

                # Remove from the running task dictionary - already under lock protection
                if task_id in self._running_tasks:
                    del self._running_tasks[task_id]

            # Update task status
            if result not in ["timeout action", "cancelled action", "failed action"]:
                task_status_manager.add_task_status(task_id, None, "completed", None, time.time(), None, None, None)

            # Check if all tasks are completed - Atomicity check required
            with self._lock:
                if self._task_queue.empty() and len(self._running_tasks) == 0:
                    self._reset_idle_timer()

    # The task scheduler closes the countdown
    def _reset_idle_timer(self) -> None:
        """
        Reset the idle timer.
        """
        with self._idle_timer_lock:
            if self._idle_timer is not None:
                self._idle_timer.cancel()
            self._idle_timer = threading.Timer(self._idle_timeout, self._idle_timeout_callback)
            self._idle_timer.daemon = True
            self._idle_timer.start()

    def _idle_timeout_callback(self) -> None:
        """
        Callback for idle timeout.
        """
        self.stop_scheduler()

    def _cancel_idle_timer(self) -> None:
        """
        Cancel the idle timer.
        """
        with self._idle_timer_lock:
            if self._idle_timer is not None:
                self._idle_timer.cancel()
                self._idle_timer = None

    def _clear_task_queue(self) -> None:
        """
        Clear the task queue.
        """
        try:
            while True:
                self._task_queue.get_nowait()
        except queue.Empty:
            pass

    def _join_scheduler_thread(self) -> None:
        """
        Wait for the scheduler thread to finish.
        """
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5.0)  # Add a timeout to prevent waiting indefinitely

    def force_stop_task(self,
                        task_id: str) -> bool:
        """
        Force stop a task by its task ID.

        Args:
            task_id: Task ID.

        Returns:
            Whether the task was successfully force stopped.
        """
        # Use a lock to protect access to the task dictionary during execution
        with self._lock:
            task_info = self._running_tasks.get(task_id)
            if not task_info:
                logger.warning(f"task | {task_id} | does not exist or is already completed")
                return False

            future = task_info[0]

        # Perform cancellation operations outside the lock to avoid deadlocks.
        try:
            if not future.running():
                future.cancel()
            else:
                # First ensure that the task is not paused.
                if platform.system() == "Windows":
                    _task_manager.resume_task(task_id)
                _task_manager.terminate_task(task_id)

            task_status_manager.add_task_status(task_id, None, "cancelled", None, time.time(), None, None,
                                                "io_liner_task")
            return True
        except Exception as e:
            logger.error(f"task | {task_id} | error during force stop: {e}")
            return False

    def pause_task(self,
                   task_id: str) -> bool:
        """
        Pause a task by its task ID.

        Args:
            task_id: Task ID.

        Returns:
            Whether the task was successfully paused.
        """
        # Use a lock to protect access to and modification of the result dictionary.
        with self._lock:
            if task_id not in self._running_tasks:
                logger.warning(f"task | {task_id} | does not exist or is already completed")
                return False

        if not platform.system() == "Windows":
            logger.warning(f"Pause and resume functionality is not supported on Linux and Mac!")
            return False

        try:
            _task_manager.pause_task(task_id)
            task_status_manager.add_task_status(task_id, None, "paused", None, None, None, None, "io_liner_task")
            logger.info(f"task | {task_id} | paused")
            return True
        except Exception as e:
            logger.error(f"task | {task_id} | error during pause: {e}")
            return False

    def resume_task(self,
                    task_id: str) -> bool:
        """
        Resume a task by its task ID.

        Args:
            task_id: Task ID.

        Returns:
            Whether the task was successfully resumed.
        """
        # Use a lock to protect access to and modification of the result dictionary.
        with self._lock:
            if task_id not in self._running_tasks:
                logger.warning(f"task | {task_id} | does not exist or is already completed")
                return False

        if not platform.system() == "Windows":
            logger.warning(f"Pause and resume functionality is not supported on Linux and Mac!")
            return False

        try:
            _task_manager.resume_task(task_id)
            task_status_manager.add_task_status(task_id, None, "running", None, None, None, None, "io_liner_task")
            logger.info(f"task | {task_id} | resumed")
            return True
        except Exception as e:
            logger.error(f"task | {task_id} | error during resume: {e}")
            return False

    # Obtain the information returned by the corresponding task
    def get_task_result(self,
                        task_id: str) -> Optional[Any]:
        """
        Get the result of a task. If there is a result, return and delete the oldest result; if no result, return None.

        Args:
            task_id: Task ID.

        Returns:
            Task return result, or None if the task is not completed or does not exist.
        """
        # Use a lock to protect access to and modification of the result dictionary.
        with self._lock:
            if task_id in self._task_results:
                result = self._task_results[task_id][0]
                del self._task_results[task_id]
                return result
        return None


io_liner_task = IoLinerTask()
