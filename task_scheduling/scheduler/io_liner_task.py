# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import queue
import threading
import math
import time

from concurrent.futures import ThreadPoolExecutor, Future
from functools import partial
from typing import Callable, Dict, Tuple, Optional, Any

from ..common import logger, config
from ..manager import task_status_manager
from ..control import ThreadTaskManager
from ..handling import TimeoutException, ThreadSuspender, StopException, ThreadingTimeout, ThreadTerminator
from .utils import TaskCounter

# Create Manager instance
_task_counter = TaskCounter("io_liner_task")
_task_manager = ThreadTaskManager()
_threadsuspender = ThreadSuspender()
_threadterminator = ThreadTerminator()


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
    timeout_processing, task_name, task_id, func, priority, args, kwargs = task

    return_results = None
    try:
        with _threadterminator.terminate_control() as terminate_ctx:
            with _threadsuspender.suspend_context() as pause_ctx:

                _task_manager.add(None, terminate_ctx, pause_ctx, task_id)

                task_status_manager.add_task_status(task_id, None, "running", time.time(), None, None, None, None)
                logger.debug(f"Start running task, task ID: {task_id}")

                if timeout_processing:
                    with ThreadingTimeout(seconds=config["watch_dog_time"], swallow_exc=False):
                        return_results = func(*args, **kwargs)
                else:
                    return_results = func(*args, **kwargs)

        _task_manager.remove(task_id)
    except TimeoutException:
        logger.warning(f"task | {task_id} | timed out, forced termination")
        task_status_manager.add_task_status(task_id, None, "timeout", None, None, None, None, None)
        return_results = "timeout action"
    except StopException:
        logger.warning(f"task | {task_id} | was cancelled")
        task_status_manager.add_task_status(task_id, None, "cancelled", None, None, None, None, None)
        return_results = "cancelled action"
    except Exception as e:
        if config["exception_thrown"]:
            raise

        logger.error(f"task | {task_id} | execution failed: {e}")
        task_status_manager.add_task_status(task_id, None, "failed", None, None, e, None, None)
        return_results = "failed action"

    finally:
        if _task_manager.check(task_id):
            _task_manager.remove(task_id)

    return return_results


class IoLinerTask:
    """
    Linear task manager class, responsible for managing the scheduling, execution, and monitoring of linear tasks.
    """
    __slots__ = [
        '_task_queue', '_running_tasks',
        '_lock', '_condition', '_scheduler_lock',
        '_scheduler_started', '_scheduler_stop_event', '_scheduler_thread',
        '_idle_timer', '_idle_timeout', '_idle_timer_lock',
        '_task_results'
    ]

    def __init__(self) -> None:
        """
        Initialize the IoLinerTask manager.
        """

        self._task_queue = queue.Queue()  # Task queue
        self._running_tasks = {}  # Running tasks

        self._lock = threading.Lock()  # Lock to protect access to shared resources
        self._scheduler_lock = threading.RLock()  # Reentrant lock for scheduler operations
        self._condition = threading.Condition()  # Condition variable for thread synchronization

        self._scheduler_started = False  # Whether the scheduler thread has started
        self._scheduler_stop_event = threading.Event()  # Scheduler thread stop event
        self._scheduler_thread: Optional[threading.Thread] = None  # Scheduler thread

        self._idle_timer: Optional[threading.Timer] = None  # Idle timer
        self._idle_timeout = config["max_idle_time"]  # Idle timeout, default is 60 seconds
        self._idle_timer_lock = threading.Lock()  # Idle timer lock

        self._task_results: Dict[str, Any] = {}  # Store task return results, keep up to 2 results for each task ID

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
                task_status_manager.add_task_status(task_id, None, "queuing", None, None, None, None, "io_liner_task")
                if not _task_counter.is_high_priority(priority):

                    if self._task_queue.qsize() >= config["io_liner_task"]:
                        return False

                    if task_name in [details[1] for details in self._running_tasks.values()]:
                        return False

                else:
                    if not _task_counter.add_count(math.ceil(config["io_liner_task"])):
                        return False

                if self._scheduler_stop_event.is_set() and not self._scheduler_started:
                    self._join_scheduler_thread()

                # Reduce the granularity of the lock
                task_status_manager.add_task_status(task_id, None, "waiting", None, None, None, None, None)

                self._task_queue.put((timeout_processing, task_name, task_id, func, priority, args, kwargs))

                if not self._scheduler_started:
                    self._start_scheduler()

                with self._condition:
                    self._condition.notify()

                self._cancel_idle_timer()

                return True
        except Exception as e:
            logger.error(f"task | {task_id} | error adding task: {e}")
            return e

    # Start the scheduler
    def _start_scheduler(self) -> None:
        """
        Start the scheduler thread.
        """
        self._scheduler_started = True
        self._scheduler_thread = threading.Thread(target=self._scheduler, daemon=True)
        self._scheduler_thread.start()

    # Stop the scheduler
    def stop_scheduler(self,
                       force_cleanup: bool,
                       system_operations: bool = False) -> None:
        """
        Stop the scheduler thread.

        Args:
            force_cleanup: If True, force stop all tasks and clear the queue.
                          If False, gracefully stop the scheduler (e.g., due to idle timeout).
            system_operations: System execution metrics.
        """
        with self._scheduler_lock:
            # Check if all tasks are completed
            if not self._task_queue.empty() or not len(self._running_tasks) == 0:
                if system_operations:
                    logger.warning(f"task was detected to be running, and the task stopped terminating")
                    return None

            if force_cleanup:
                logger.warning("Force stopping scheduler and cleaning up tasks")
                # Force stop all running tasks
                _task_manager.terminate_all_tasks()
                self._scheduler_stop_event.set()
            else:
                self._scheduler_stop_event.set()

            # Clear the task queue
            self._clear_task_queue()

            # Notify all waiting threads
            with self._condition:
                self._condition.notify_all()

            # Wait for the scheduler thread to finish
            self._join_scheduler_thread()

            # Reset state variables
            self._scheduler_started = False
            self._scheduler_stop_event.clear()
            self._scheduler_thread = None
            self._idle_timer = None
            self._task_results = {}

            logger.debug(
                "Scheduler and event loop have stopped, all resources have been released and parameters reset")

    # Task scheduler
    def _scheduler(self) -> None:
        """
        Scheduler function, fetch tasks from the task queue and submit them to the thread pool for execution.
        """
        with ThreadPoolExecutor(max_workers=int(config["io_liner_task"] + math.ceil(config["io_liner_task"] / 2)),
                                initializer=None) as executor:
            while not self._scheduler_stop_event.is_set():
                with self._condition:
                    while self._task_queue.empty() and not self._scheduler_stop_event.is_set():
                        self._condition.wait()

                    if self._scheduler_stop_event.is_set():
                        break

                    if self._task_queue.qsize() == 0:
                        continue

                    task = self._task_queue.get()

                timeout_processing, task_name, task_id, func, priority, args, kwargs = task

                with self._lock:
                    future = executor.submit(_execute_task, task)
                    self._running_tasks[task_id] = [future, task_name, priority]

                    future.add_done_callback(partial(self._task_done, task_id))
                _task_counter.schedule_tasks(self._running_tasks, self.pause_task, self.resume_task)

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
        try:
            result = future.result()  # Get task result, exceptions will be raised here

            # Store task return results, keep up to 2 results
            if result not in ["timeout action", "cancelled action", "failed action"]:
                if result is not None:
                    with self._lock:
                        self._task_results[task_id] = [result, time.time()]
                else:
                    with self._lock:
                        self._task_results[task_id] = ["completed action", time.time()]
                task_status_manager.add_task_status(task_id, None, "completed", None, time.time(), None, None, None)
            else:
                with self._lock:
                    self._task_results[task_id] = [result, time.time()]

        finally:
            # Ensure the Future object is deleted
            with self._lock:
                if task_id in self._running_tasks:
                    del self._running_tasks[task_id]

            # Check if all tasks are completed
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
            self._idle_timer = threading.Timer(self._idle_timeout, self.stop_scheduler, args=(False, True,))
            self._idle_timer.daemon = True
            self._idle_timer.start()

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
        while not self._task_queue.empty():
            self._task_queue.get(timeout=1.0)

    def _join_scheduler_thread(self) -> None:
        """
        Wait for the scheduler thread to finish.
        """
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join()

    def force_stop_task(self,
                        task_id: str) -> bool:
        """
        Force stop a task by its task ID.

        Args:
            task_id: Task ID.

        Returns:
            Whether the task was successfully force stopped.
        """
        if not self._running_tasks.get(task_id, None):
            logger.warning(f"task | {task_id} | does not exist or is already completed")
            return False

        future = self._running_tasks[task_id][0]
        if not future.running():
            future.cancel()
        else:
            # First ensure that the task is not paused.
            _task_manager.resume_task(task_id)
            _task_manager.terminate_task(task_id)

        task_status_manager.add_task_status(task_id, None, "cancelled", None, None, None, None, None)
        return True

    def pause_task(self,
                   task_id: str) -> bool:
        """
        Pause a task by its task ID.

        Args:
            task_id: Task ID.

        Returns:
            Whether the task was successfully paused.
        """
        if self._running_tasks.get(task_id) is None and not config["thread_management"]:
            logger.warning(f"task | {task_id} | does not exist or is already completed")
            return False

        _task_manager.pause_task(task_id)
        task_status_manager.add_task_status(task_id, None, "paused", None, None, None, None, None)

        return True

    def resume_task(self,
                    task_id: str) -> bool:
        """
        Resume a task by its task ID.

        Args:
            task_id: Task ID.

        Returns:
            Whether the task was successfully resumed.
        """
        if self._running_tasks.get(task_id) is None and not config["thread_management"]:
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
        if task_id in self._task_results:
            result = self._task_results[task_id][0]
            with self._lock:
                del self._task_results[task_id]
            return result
        return None


io_liner_task = IoLinerTask()
