# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Timer-based task execution module.

This module provides a task scheduler for timer-based tasks with support for
delayed execution and daily recurring tasks using priority queues.
"""
import queue
import threading
import time
import platform

from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timedelta
from functools import partial
from typing import Callable, Dict, List, Tuple, Optional, Any

from ..common import logger, config
from ..manager import task_status_manager
from ..control import ThreadTaskManager
from ..handling import ThreadTerminator, StopException, ThreadingTimeout, TimeoutException, ThreadSuspender
from .utils import retry_on_error_decorator_check

# Create Manager instance
_task_manager = ThreadTaskManager()
_threadterminator = ThreadTerminator()
_threadsuspender = ThreadSuspender()


def _execute_task(task: Tuple[bool, str, str, Callable, Tuple, Dict]) -> Any:
    """
    Execute a task and handle its status.

    Args:
        task: A tuple containing task details.
            - timeout_processing: Whether timeout processing is enabled.
            - task_name: Name of the task.
            - task_id: ID of the task.
            - func: The function to execute.
            - args: Arguments to pass to the function.
            - kwargs: Keyword arguments to pass to the function.

    Returns:
        Result of the task execution or error message.
    """
    timeout_processing, task_name, task_id, func, args, kwargs = task
    logger.debug(f"Start running task, task ID: {task_id}")

    try:
        with _threadterminator.terminate_control() as terminate_ctx:
            with _threadsuspender.suspend_context() as pause_ctx:
                _task_manager.add(None, terminate_ctx, pause_ctx, task_id)
                task_status_manager.add_task_status(task_id, None, "running", time.time(), None, None,
                                                    None, None)

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
        task_status_manager.add_task_status(task_id, None, "timeout", None, None, None,
                                            None, None)
        result = "timeout action"
    except StopException:
        logger.warning(f"task | {task_id} | cancelled, forced termination")
        task_status_manager.add_task_status(task_id, None, "cancelled", None, None, None,
                                            None, None)
        result = "cancelled action"
    except Exception as error:
        if config["exception_thrown"]:
            raise

        logger.error(f"task | {task_id} | execution failed: {error}")
        task_status_manager.add_task_status(task_id, None, "failed", None, None, error,
                                            None, None)
        result = "failed action"

    finally:
        if _task_manager.exists(task_id):
            _task_manager.remove(task_id)

    return result


class TimerTask:
    """
    Timer task manager class, responsible for scheduling, executing, and monitoring timer-based tasks.
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
        Initialize the TimerTask manager.
        """
        self._task_queue = queue.PriorityQueue()  # Task queue with priority based on execution time
        self._running_tasks = {}  # Running tasks

        self._lock = threading.Lock()  # Lock to protect access to shared resources
        self._scheduler_lock = threading.RLock()  # Reentrant lock for scheduler operations
        self._condition = threading.Condition(self._lock)  # Condition variable using existing lock for synchronization

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
                 delay: Optional[int],
                 daily_time: Optional[str],
                 timeout_processing: bool,
                 task_name: str,
                 task_id: str,
                 func: Callable,
                 *args,
                 **kwargs) -> Any:
        """
        Add a task to the task queue.

        Args:
            delay: Delay in seconds before the task should be executed (only once).
            daily_time: Specific time in "HH:MM" format for daily task execution.
            timeout_processing: Whether to enable timeout processing.
            task_name: Task name (can be repeated).
            task_id: Task ID (must be unique).
            func: Task function.
            *args: Positional arguments for the task function.
            **kwargs: Keyword arguments for the task function.

        Returns:
            Whether the task was successfully added.
        """
        try:
            with self._scheduler_lock:
                if self._scheduler_stop_event.is_set() and not self._scheduler_started:
                    self._join_scheduler_thread()

                if delay is not None:
                    # Schedule task to run after a delay (only once)
                    execution_time = time.time() + delay
                elif daily_time is not None:
                    # Schedule task to run daily at a specific time
                    daily_time_obj = datetime.strptime(daily_time, "%H:%M")
                    now = datetime.now()
                    scheduled_time = datetime(now.year, now.month, now.day, daily_time_obj.hour, daily_time_obj.minute)
                    if scheduled_time < now:
                        scheduled_time += timedelta(days=1)
                    execution_time = scheduled_time.timestamp()
                else:
                    logger.error(f"task | {task_id} | no scheduling parameters provided")
                    return False

                # Reduce the granularity of the lock
                task_status_manager.add_task_status(task_id, None, "waiting", None, None, None,
                                                    None, "timer_task")

                self._task_queue.put((execution_time, timeout_processing, task_name, task_id, func, args, kwargs))

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

        # Notify all waiting threads first
        with self._condition:
            self._condition.notify_all()

        with self._scheduler_lock:
            # Check if all tasks are completed - use atomic check with lock
            if system_operations:
                with self._lock:
                    if not self._task_queue.empty() or len(self._running_tasks) != 0:
                        logger.warning(f"task was detected to be running, and the task stopped terminating")
                        return None

            # Terminate the task
            _task_manager.terminate_all_tasks()

            # Ensure the executor is properly shut down
            if self._executor:
                # Use wait=True for safe shutdown in No GIL environment
                self._executor.shutdown(wait=False, cancel_futures=True)

            # Clear the task queue - use atomic operation with lock
            self._clear_task_queue()

            # Wait for the scheduler thread to finish
            self._join_scheduler_thread()

            self._wait_tasks_end()
            # Reset state variables - use atomic operations with locks
            with self._lock:
                self._scheduler_started = False
                self._running_tasks.clear()
                self._task_results.clear()

            self._scheduler_thread = None

            # Cancel idle timer safely
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

    # Scheduler function
    def _scheduler(self) -> None:
        """
        Scheduler function, fetch tasks from the task queue and submit them to the thread pool for execution.
        """
        with ThreadPoolExecutor(max_workers=int(config["timer_task"])) as executor:
            self._executor = executor
            while not self._scheduler_stop_event.is_set():
                with self._condition:
                    # Use loop and timeout to prevent spurious wakeup
                    while (self._task_queue.empty() and
                           not self._scheduler_stop_event.is_set()):
                        self._condition.wait(timeout=1.0)  # Add timeout to prevent permanent waiting

                    if self._scheduler_stop_event.is_set():
                        break

                    # Check queue state again due to possible spurious wakeup or timeouts
                    if self._task_queue.empty():
                        continue

                    # Get the next task atomically
                    execution_time, timeout_processing, task_name, task_id, func, args, kwargs = self._task_queue.get()

                    # If task is not ready yet, put it back and wait
                    if execution_time > time.time():
                        self._task_queue.put(
                            (execution_time, timeout_processing, task_name, task_id, func, args, kwargs))
                        wait_time = max(0.1, min(execution_time - time.time(), 60.0))  # Reasonable wait limits
                        self._condition.wait(wait_time)
                        continue

                # Submit task for execution with lock protection
                with self._lock:
                    future = executor.submit(_execute_task,
                                             (timeout_processing, task_name, task_id, func, args, kwargs))
                    self._running_tasks[task_id] = [future, task_name]

                    future.add_done_callback(
                        partial(self._task_done, task_id, timeout_processing, task_name, func, args, kwargs))

    # A function that executes a task
    def _task_done(self,
                   task_id: str,
                   timeout_processing: bool,
                   task_name: str,
                   func: Callable,
                   args: Tuple,
                   kwargs: Dict,
                   future: Future) -> None:
        """
        Callback function after a task is completed.

        Args:
            task_id: Task ID.
            timeout_processing: Whether timeout processing is enabled.
            task_name: Task name.
            func: Task function.
            args: Positional arguments for the task function.
            kwargs: Keyword arguments for the task function.
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
            # Other exceptions are already handled in _execute_task
            result = "failed action"
        finally:
            # Store task results with lock protection
            with self._lock:
                if result not in ["timeout action", "cancelled action", "failed action"]:
                    if result is not None:
                        self._task_results[task_id] = [result, time.time()]
                    else:
                        self._task_results[task_id] = ["completed action", time.time()]
                else:
                    self._task_results[task_id] = [result, time.time()]

                # Remove from running tasks - already under lock protection
                if task_id in self._running_tasks:
                    del self._running_tasks[task_id]

            # Update task status
            if result not in ["timeout action", "cancelled action", "failed action"]:
                task_status_manager.add_task_status(task_id, None, "completed", None, time.time(), None, None, None)

            # Check if the task is a daily task and reschedule it for the next day
            daily_time = kwargs.get('daily_time')
            if daily_time:
                try:
                    daily_time_obj = datetime.strptime(daily_time, "%H:%M")
                    now = datetime.now()
                    scheduled_time = datetime(now.year, now.month, now.day, daily_time_obj.hour, daily_time_obj.minute)
                    if scheduled_time < now:
                        scheduled_time += timedelta(days=1)
                    execution_time = scheduled_time.timestamp()
                    # Put the task back to queue for next execution
                    self._task_queue.put((execution_time, timeout_processing, task_name, task_id, func, args, kwargs))
                except ValueError:
                    # If daily_time is not a valid time string, do not reschedule
                    logger.error(
                        f"task | {task_id} | daily_time is not a valid time string, not rescheduling")

            # Check if all tasks are completed - use atomic check with lock
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
            self._scheduler_thread.join(timeout=5.0)  # Add timeout to prevent permanent waiting

    def force_stop_task(self,
                        task_id: str) -> bool:
        """
        Force stop a task by its task ID.

        Args:
            task_id: Task ID.

        Returns:
            Whether the task was successfully force stopped.
        """
        # Use lock protection for running tasks dictionary access
        with self._lock:
            task_info = self._running_tasks.get(task_id)
            if not task_info:
                logger.warning(f"task | {task_id} | does not exist or is already completed")
                return False

            future = task_info[0]

        # Perform cancellation outside the lock to avoid deadlocks
        try:
            if not future.running():
                future.cancel()
            else:
                # First ensure that the task is not paused.
                if platform.system() == "Windows":
                    _task_manager.resume_task(task_id)
                _task_manager.terminate_task(task_id)

            task_status_manager.add_task_status(task_id, None, "cancelled", None, time.time(), None, None, "timer_task")
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
        # Use lock protection for running tasks dictionary access
        with self._lock:
            if task_id not in self._running_tasks:
                logger.warning(f"task | {task_id} | does not exist or is already completed")
                return False

        if not platform.system() == "Windows":
            logger.warning(f"Pause and resume functionality is not supported on Linux and Mac!")
            return False

        try:
            _task_manager.pause_task(task_id)
            task_status_manager.add_task_status(task_id, None, "paused", None, None, None, None, "timer_task")
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
        # Use lock protection for running tasks dictionary access
        with self._lock:
            if task_id not in self._running_tasks:
                logger.warning(f"task | {task_id} | does not exist or is already completed")
                return False

        _task_manager.resume_task(task_id)
        task_status_manager.add_task_status(task_id, None, "running", None, None, None, None, None)

        return True

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
        # Use lock protection for results dictionary access and modification
        with self._lock:
            if task_id not in self._running_tasks:
                logger.warning(f"task | {task_id} | does not exist or is already completed")
                return False

        if not platform.system() == "Windows":
            logger.warning(f"Pause and resume functionality is not supported on Linux and Mac!")
            return False

        try:
            _task_manager.resume_task(task_id)
            task_status_manager.add_task_status(task_id, None, "running", None, None, None, None, "timer_task")
            logger.info(f"task | {task_id} | resumed")
            return True
        except Exception as e:
            logger.error(f"task | {task_id} | error during resume: {e}")
            return False


timer_task = TimerTask()
