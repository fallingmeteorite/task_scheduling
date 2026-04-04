# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""IO-bound linear task execution module.

This module provides a task scheduler for IO-bound linear tasks using
thread pool execution with priority-based scheduling and timeout handling.
"""
import dill
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from functools import partial
from typing import Callable, Dict, Tuple, Optional, Any, List

from task_scheduling.common import logger, config
from task_scheduling.control import ThreadTaskManager
from task_scheduling.handling import TimeoutException, ThreadSuspender, StopException, ThreadingTimeout, \
    ThreadTerminator
from task_scheduling.manager import task_status_manager
from task_scheduling.scheduler.utils import TaskCounter, retry_on_error_decorator_check
from task_scheduling.result_server import store_task_result

# Create Manager instance
_task_counter = TaskCounter("io_liner_task")
_task_manager = ThreadTaskManager()


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
    result = None
    timeout_processing, task_name, task_id, func, priority, args, kwargs = task
    logger.debug(f"Start running task, task ID: {task_id}")
    try:
        with ThreadTerminator().terminate_control() as terminate_ctx:
            with ThreadSuspender() as pause_ctx:

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
        '_task_queue', '_running_tasks', '_running_task_names',
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
        self._running_task_names = set()  # Running task names for O(1) duplicate checks

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
            need_add_high = False
            # Capacity check (lock only for shared state)
            with self._lock:
                # Atomic Check Queue Size and Running Tasks
                queue_size = self._task_queue.qsize()

                if queue_size >= config["io_liner_task"] or len(self._running_tasks) >= config[
                    "io_liner_task"]:
                    if _task_counter.is_high_priority(priority):
                        if _task_counter.is_high_priority_full(config["io_liner_task"]):
                            return False
                        # Prevent circular locking
                        need_add_high = True
                    return False

                if task_name in self._running_task_names:
                    return False

            if need_add_high:
                _task_counter.add_high_priority_task(task_id, self._running_tasks)

            # Scheduler state handling (protected by scheduler_lock)
            with self._scheduler_lock:
                if self._scheduler_stop_event.is_set() and not self._scheduler_started:
                    self._join_scheduler_thread()

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
            # Check if all tasks are completed (only when system_operations)
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

            # Clear the task queue
            self._clear_task_queue()

            # Reset state variables
            with self._lock:
                self._scheduler_started = False
                self._running_tasks.clear()
                self._running_task_names.clear()
                self._task_results.clear()

            self._scheduler_thread = None

            # Cancel idle timer
            with self._idle_timer_lock:
                if self._idle_timer is not None:
                    self._idle_timer.cancel()
                    self._idle_timer = None

            logger.debug(
                "Scheduler and event loop have stopped, all resources have been released and parameters reset")

        # Wait for scheduler thread and running tasks to finish (outside lock)
        self._join_scheduler_thread()
        self._wait_tasks_end()

        return None

    def _wait_tasks_end(self) -> None:
        """
        Wait for all tasks to finish
        """
        while True:
            with self._lock:
                if len(self._running_tasks) == 0:
                    break
            time.sleep(0.01)

    # Task scheduler
    def _scheduler(self) -> None:
        """
        Scheduler function, fetch tasks from the task queue and submit them to the thread pool for execution.
        """
        with ThreadPoolExecutor(max_workers=int(config["io_liner_task"] * 2)
                                ) as executor:
            self._executor = executor
            while not self._scheduler_stop_event.is_set():
                with self._condition:
                    # Use loops and timeouts to prevent spurious wakeup
                    while (self._task_queue.empty() and
                           not self._scheduler_stop_event.is_set()):
                        self._condition.wait()

                    if self._scheduler_stop_event.is_set():
                        break

                    # Check the queue status again, as it may have been falsely awakened or timed out.
                    try:
                        task = self._task_queue.get_nowait()
                    except queue.Empty:
                        continue

                timeout_processing, task_name, task_id, func, priority, args, kwargs = task

                # Submit task outside lock to reduce lock hold time
                future = executor.submit(_execute_task, task)
                with self._lock:
                    self._running_tasks[task_id] = [future, task_name, priority]
                    self._running_task_names.add(task_name)

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
        _task_counter.remove_high_priority_task(task_id)
        try:
            result = future.result()  # Get task result, exceptions will be raised here

        except StopException:
            logger.warning(f"task | {task_id} | was cancelled")
            task_status_manager.add_task_status(task_id, None, "cancelled", None, None, None, None, None)
            result = "cancelled action"

        except Exception as error:
            # Other exceptions have already been handled in _execute_task.
            task_status_manager.add_task_status(task_id, None, "cancelled", None, None, error, None, None)
            result = "failed action"

        finally:
            # Prepare data for network storage (outside lock)
            network_storage = config["network_storage_results"]
            store_data = None
            if network_storage:
                store_data = dill.dumps(result)

            # Lock-protected section: update local results and running tasks
            with self._lock:
                if result not in ["timeout action", "cancelled action", "failed action"]:
                    if result is not None:
                        if not network_storage:
                            self._task_results[task_id] = [result, time.time()]
                    else:
                        if not network_storage:
                            self._task_results[task_id] = ["completed action", time.time()]
                else:
                    if not network_storage:
                        self._task_results[task_id] = [result, time.time()]

                # Remove from the running task dictionary
                task_info = self._running_tasks.pop(task_id, None)
                if task_info is not None:
                    self._running_task_names.discard(task_info[1])

                # Check if all tasks are completed
                if self._task_queue.empty() and len(self._running_tasks) == 0:
                    self._reset_idle_timer()

            # Perform network storage outside lock (I/O operation)
            if network_storage:
                store_task_result(task_id, store_data)

            # Update task status
            if result not in ["timeout action", "cancelled action", "failed action"]:
                task_status_manager.add_task_status(task_id, None, "completed", None, time.time(), None, None, None)

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
            self._scheduler_thread.join(timeout=1.0)  # Add a timeout to prevent waiting indefinitely

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
                _task_manager.resume_task(task_id)
                _task_manager.terminate_task(task_id)

            task_status_manager.add_task_status(task_id, None, "cancelled", None, time.time(), None, None,
                                                "io_liner_task")
            return True
        except Exception as error:
            logger.error(f"task | {task_id} | error during force stop: {error}")
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

        try:
            _task_manager.pause_task(task_id)
            task_status_manager.add_task_status(task_id, None, "paused", None, None, None, None, "io_liner_task")
            logger.info(f"task | {task_id} | paused")
            return True
        except Exception as error:
            logger.error(f"task | {task_id} | error during pause: {error}")
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

        try:
            _task_manager.resume_task(task_id)
            task_status_manager.add_task_status(task_id, None, "running", None, None, None, None, "io_liner_task")
            logger.info(f"task | {task_id} | resumed")
            return True
        except Exception as error:
            logger.error(f"task | {task_id} | error during resume: {error}")
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
