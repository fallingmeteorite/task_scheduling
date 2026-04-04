# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Timer-based task execution module.

This module provides a task scheduler for timer-based tasks with support for
delayed execution and daily recurring tasks using time bucket queue.
"""
import dill
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timedelta
from functools import partial
from typing import Callable, Dict, List, Tuple, Optional, Any

from task_scheduling.common import logger, config
from task_scheduling.control import ThreadTaskManager
from task_scheduling.handling import ThreadTerminator, StopException, ThreadingTimeout, TimeoutException, \
    ThreadSuspender
from task_scheduling.manager import task_status_manager
from task_scheduling.scheduler.utils import retry_on_error_decorator_check
from task_scheduling.result_server import store_task_result

from task_scheduling.scheduler.utils import TimeBucketQueue

# Create Manager instance
_task_manager = ThreadTaskManager()


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
        with ThreadTerminator().terminate_control() as terminate_ctx:
            with ThreadSuspender() as pause_ctx:
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
        '_task_queue', '_running_tasks', '_running_task_names',
        '_lock', '_condition', '_scheduler_lock',
        '_scheduler_started', '_scheduler_stop_event', '_scheduler_thread', '_task_add_lock',
        '_idle_timer', '_idle_timeout', '_idle_timer_lock',
        '_task_results',
        '_executor'
    ]

    def __init__(self) -> None:
        """
        Initialize the TimerTask manager.
        """
        # Use TimeBucketQueue instead of PriorityQueue
        self._task_queue = TimeBucketQueue()
        self._running_tasks = {}  # Running tasks
        self._running_task_names = set()  # Running task names for O(1) duplicate checks

        self._lock = threading.Lock()  # Lock to protect access to shared resources
        self._scheduler_lock = threading.RLock()  # Reentrant lock for scheduler operations
        self._condition = threading.Condition(self._lock)  # Condition variable using existing lock for synchronization
        self._task_add_lock = False

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
            while self._task_add_lock:
                time.sleep(0.01)

            # Check scheduler state (protected by scheduler_lock)
            with self._scheduler_lock:
                if self._scheduler_stop_event.is_set() and not self._scheduler_started:
                    self._join_scheduler_thread()

            # Capacity check (lock only for shared state)
            with self._lock:

                if len(self._running_tasks) >= config["io_liner_task"]:
                    return False

                if task_name in self._running_task_names:
                    return False

            # Calculate execution time (no lock needed)
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

            # Status update (thread-safe, no lock needed)
            task_status_manager.add_task_status(task_id, None, "waiting", None, None, None,
                                                None, "timer_task")

            # Put into time bucket queue
            self._task_queue.put(execution_time, (timeout_processing, task_name, task_id, func, args, kwargs))
            with self._lock:
                self._task_add_lock = True

            # Start scheduler if needed (protected by scheduler_lock)
            with self._scheduler_lock:
                if not self._scheduler_started:
                    self._start_scheduler()

            # Wake up scheduler thread (it may be waiting for new tasks)
            with self._condition:
                self._condition.notify()

            # Cancel idle timer (has its own lock)
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

        # Terminate the task (no lock needed)
        _task_manager.terminate_all_tasks()

        # Ensure the executor is properly shut down
        if self._executor:
            # Use wait=True for safe shutdown in No GIL environment
            self._executor.shutdown(wait=False, cancel_futures=True)

        # Clear the task queue (no lock needed)
        self._clear_task_queue()

        # Wait for the scheduler thread to finish (no lock needed)
        self._join_scheduler_thread()

        self._wait_tasks_end()

        # Reset state variables - use atomic operations with locks
        with self._lock:
            self._scheduler_started = False
            self._running_tasks.clear()
            self._running_task_names.clear()
            self._task_results.clear()
            self._task_add_lock = False

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

    # Scheduler function (refactored to use time bucket queue)
    def _scheduler(self) -> None:
        """
        Scheduler function, fetch tasks from the time bucket queue and submit them to the thread pool for execution.
        """
        with ThreadPoolExecutor(max_workers=int(config["timer_task"])) as executor:
            self._executor = executor
            while not self._scheduler_stop_event.is_set():
                # Wait until there is a task and the earliest task's time has arrived
                with self._condition:
                    # Loop to check conditions, avoiding spurious wakeups
                    while not self._scheduler_stop_event.is_set():
                        if self._task_queue.empty():
                            # Queue is empty, wait for new tasks (max 1 second to also check stop event)
                            self._condition.wait(timeout=1.0)
                            continue

                        # Get the next execution time
                        next_time = self._task_queue.peek_next_time()
                        now = time.time()
                        if next_time > now:
                            # Time not reached, wait until execution time or new task arrives
                            wait_time = min(next_time - now, 60.0)  # Max 60 seconds to avoid long blocking
                            self._condition.wait(timeout=wait_time)
                            continue
                        else:
                            # Tasks are ready, break out of waiting loop
                            break

                # Conditions satisfied, exit lock-protected area then fetch ready buckets (avoid holding lock for too long)
                if self._scheduler_stop_event.is_set():
                    break

                # Get all buckets whose execution time has arrived (thread-safe internally)
                ready_buckets = self._task_queue.get_ready_buckets(time.time())

                # Process each bucket
                for _, tasks in ready_buckets:
                    for task in tasks:
                        # task structure: (timeout_processing, task_name, task_id, func, args, kwargs)
                        timeout_processing, task_name, task_id, func, args, kwargs = task

                        # Submit task to thread pool
                        future = executor.submit(_execute_task, task)

                        # Update running tasks dictionary (needs lock protection)
                        with self._lock:
                            self._running_tasks[task_id] = [future, task_name]
                            self._running_task_names.add(task_name)
                            self._task_add_lock = False

                        # Add completion callback (pass full task parameters for rescheduling etc.)
                        future.add_done_callback(
                            partial(self._task_done, task_id, timeout_processing, task_name, func, args, kwargs)
                        )

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

        except Exception as error:
            # Other exceptions are already handled in _execute_task
            task_status_manager.add_task_status(task_id, None, "failed", None, None, error, None, None)
            result = "failed action"

        finally:
            # Prepare result for storage (without lock)
            network_storage = config["network_storage_results"]
            serialized_result = None
            if network_storage:
                serialized_result = dill.dumps(result)

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

                # Remove from running tasks - already under lock protection
                if task_id in self._running_tasks:
                    task_info = self._running_tasks.pop(task_id, None)
                    self._running_task_names.discard(task_info[1])

            # Perform network storage outside lock (I/O operation)
            if network_storage:
                store_task_result(task_id, serialized_result)

            # Update task status (thread-safe, no lock needed)
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

                    # Build task tuple and put back into time bucket queue
                    task_tuple = (timeout_processing, task_name, task_id, func, args, kwargs)
                    self._task_queue.put(execution_time, task_tuple)

                    # Wake up scheduler thread to process the newly added task immediately
                    with self._condition:
                        self._condition.notify()
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
        self._task_queue.clear()

    def _join_scheduler_thread(self) -> None:
        """
        Wait for the scheduler thread to finish.
        """
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=1.0)  # Add timeout to prevent permanent waiting

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
                _task_manager.resume_task(task_id)
                _task_manager.terminate_task(task_id)

            task_status_manager.add_task_status(task_id, None, "running", None, time.time(), None, None, "timer_task")
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
        # Use lock protection for running tasks dictionary access
        with self._lock:
            if task_id not in self._running_tasks:
                logger.warning(f"task | {task_id} | does not exist or is already completed")
                return False

        try:
            _task_manager.pause_task(task_id)
            task_status_manager.add_task_status(task_id, None, "paused", None, None, None, None, "timer_task")
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


timer_task = TimerTask()
