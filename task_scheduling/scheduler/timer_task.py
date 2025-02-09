# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timedelta
from functools import partial
from typing import Callable, Dict, List, Tuple, Optional, Any

from ..common import logger
from ..config import config
from ..manager import task_status_manager
from ..stopit import ThreadTaskManager, skip_on_demand, StopException, ThreadingTimeout, TimeoutException

# Create Manager instance
task_manager = ThreadTaskManager()


def _execute_task(task: Tuple[bool, str, str, Callable, Tuple, Dict]) -> Any:
    """
    Execute a task and handle its status.

    Args:
        task (Tuple[bool, str, str, Callable, Tuple, Dict]): A tuple containing task details.
            - timeout_processing (bool): Whether timeout processing is enabled.
            - task_name (str): Name of the task.
            - task_id (str): ID of the task.
            - func (Callable): The function to execute.
            - args (Tuple): Arguments to pass to the function.
            - kwargs (Dict): Keyword arguments to pass to the function.

    Returns:
        Any: Result of the task execution or error message.
    """
    timeout_processing, task_name, task_id, func, args, kwargs = task

    return_results = None
    try:
        task_status_manager.add_task_status(task_id, None, "running", time.time(), None, None,
                                            None)

        logger.info(f"Start running timer task, task ID: {task_id}")
        if timeout_processing:
            with ThreadingTimeout(seconds=config["watch_dog_time"], swallow_exc=False):
                with skip_on_demand() as skip_ctx:
                    task_manager.add(None, skip_ctx, None, task_id)
                    return_results = func(*args, **kwargs)
        else:
            with skip_on_demand() as skip_ctx:
                task_manager.add(None, skip_ctx, None, task_id)
                return_results = func(*args, **kwargs)
        task_manager.remove(task_id)
    except TimeoutException:
        logger.warning(f"Timer task | {task_id} | timed out, forced termination")
        task_status_manager.add_task_status(task_id, None, "timeout", None, None, None,
                                            None)
        return_results = "error happened"
    except StopException:
        logger.warning(f"Timer task | {task_id} | cancelled, forced termination")
        task_status_manager.add_task_status(task_id, None, "cancelled", None, None, None,
                                            None)
        return_results = "error happened"
    except Exception as e:
        logger.error(f"Timer task | {task_id} | execution failed: {e}")
        task_status_manager.add_task_status(task_id, None, "failed", None, None, e,
                                            None)
        return_results = "error happened"
    finally:
        if task_manager.check(task_id):
            task_manager.remove(task_id)
        return return_results


class TimerTask:
    """
    Timer task manager class, responsible for scheduling, executing, and monitoring timer-based tasks.
    """
    __slots__ = [
        'task_queue', 'running_tasks',
        'lock', 'condition', 'scheduler_lock',
        'scheduler_started', 'scheduler_stop_event', 'scheduler_thread',
        'idle_timer', 'idle_timeout', 'idle_timer_lock',
        'task_results'
    ]

    def __init__(self) -> None:
        """
        Initialize the TimerTask manager.
        """
        self.task_queue = queue.PriorityQueue()  # Task queue with priority based on execution time
        self.running_tasks = {}  # Running tasks

        self.lock = threading.Lock()  # Lock to protect access to shared resources
        self.scheduler_lock = threading.RLock()  # Reentrant lock for scheduler operations
        self.condition = threading.Condition()  # Condition variable for thread synchronization

        self.scheduler_started = False  # Whether the scheduler thread has started
        self.scheduler_stop_event = threading.Event()  # Scheduler thread stop event
        self.scheduler_thread: Optional[threading.Thread] = None  # Scheduler thread

        self.idle_timer: Optional[threading.Timer] = None  # Idle timer
        self.idle_timeout = config["max_idle_time"]  # Idle timeout, default is 60 seconds
        self.idle_timer_lock = threading.Lock()  # Idle timer lock

        self.task_results: Dict[str, List[Any]] = {}  # Store task return results, keep up to 2 results for each task ID

    # Add the task to the scheduler
    def add_task(self,
                 delay: Optional[int],
                 daily_time: Optional[str],
                 timeout_processing: bool,
                 task_name: str,
                 task_id: str,
                 func: Callable,
                 *args,
                 **kwargs) -> bool:
        """
        Add a task to the task queue.

        Args:
            delay (Optional[int]): Delay in seconds before the task should be executed (only once).
            daily_time (Optional[str]): Specific time in "HH:MM" format for daily task execution.
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
            with self.scheduler_lock:
                if self.scheduler_stop_event.is_set() and not self.scheduler_started:
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
                    logger.error(f"Timer task | {task_id} | no scheduling parameters provided")
                    return False

                # Reduce the granularity of the lock
                task_status_manager.add_task_status(task_id, None, "waiting", None, None, None,
                                                    None)

                self.task_queue.put((execution_time, timeout_processing, task_name, task_id, func, args, kwargs))

                if not self.scheduler_started:
                    self._start_scheduler()

                with self.condition:
                    self.condition.notify()

                self._cancel_idle_timer()

                return True
        except Exception as e:
            logger.error(f"Error adding task | {task_id} |: {e}")
            return False

    # Start the scheduler
    def _start_scheduler(self) -> None:
        """
        Start the scheduler thread.
        """
        self.scheduler_started = True
        self.scheduler_thread = threading.Thread(target=self._scheduler, daemon=True)
        self.scheduler_thread.start()

    # Stop the scheduler
    def stop_scheduler(self,
                       force_cleanup: bool,
                       system_operations: bool = False) -> None:
        """
        Stop the scheduler thread.

        :param force_cleanup: If True, force stop all tasks and clear the queue.
                              If False, gracefully stop the scheduler (e.g., due to idle timeout).
        :param system_operations: System execution metrics.
        """
        with self.scheduler_lock:
            # Check if all tasks are completed
            if not self.task_queue.empty() or not len(self.running_tasks) == 0:
                if system_operations:
                    logger.warning(f"Timer task was detected to be running, and the task stopped terminating")
                    return None

            if force_cleanup:
                logger.warning("Force stopping scheduler and cleaning up tasks")
                # Force stop all running tasks
                task_manager.skip_all_tasks()
                self.scheduler_stop_event.set()
            else:
                self.scheduler_stop_event.set()

            # Clear the task queue
            self._clear_task_queue()

            # Notify all waiting threads
            with self.condition:
                self.condition.notify_all()

            # Wait for the scheduler thread to finish
            self._join_scheduler_thread()

            # Reset state variables
            self.scheduler_started = False
            self.scheduler_stop_event.clear()
            self.scheduler_thread = None
            self.idle_timer = None
            self.task_results = {}

            logger.info(
                "Scheduler and event loop have stopped, all resources have been released and parameters reset")

    # Scheduler function
    def _scheduler(self) -> None:
        """
        Scheduler function, fetch tasks from the task queue and submit them to the thread pool for execution.
        """
        with ThreadPoolExecutor(max_workers=int(config["timer_task"])) as executor:
            while not self.scheduler_stop_event.is_set():
                with self.condition:
                    while self.task_queue.empty() and not self.scheduler_stop_event.is_set():
                        self.condition.wait()

                    if self.scheduler_stop_event.is_set():
                        break

                    if self.task_queue.qsize() == 0:
                        continue

                    execution_time, timeout_processing, task_name, task_id, func, args, kwargs = self.task_queue.get()

                    if execution_time > time.time():
                        self.task_queue.put(
                            (execution_time, timeout_processing, task_name, task_id, func, args, kwargs))
                        self.condition.wait(execution_time - time.time())
                        continue

                with self.lock:
                    future = executor.submit(_execute_task,
                                             (timeout_processing, task_name, task_id, func, args, kwargs))
                    self.running_tasks[task_id] = [future, task_name]

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

        :param task_id: Task ID.
        :param timeout_processing: Whether timeout processing is enabled.
        :param task_name: Task name.
        :param func: Task function.
        :param args: Positional arguments for the task function.
        :param kwargs: Keyword arguments for the task function.
        :param future: Future object corresponding to the task.
        """
        try:
            result = future.result()  # Get task result, exceptions will be raised here
            if result != "error happened":
                task_status_manager.add_task_status(task_id, None, "completed", None, time.time(), None, None)
        finally:
            # Ensure the Future object is deleted
            with self.lock:
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]

            # Check if the task is a daily task and reschedule it for the next day
            if daily_time := kwargs.get('daily_time'):
                try:
                    daily_time_obj = datetime.strptime(daily_time, "%H:%M")
                    now = datetime.now()
                    scheduled_time = datetime(now.year, now.month, now.day, daily_time_obj.hour, daily_time_obj.minute)
                    if scheduled_time < now:
                        scheduled_time += timedelta(days=1)
                    execution_time = scheduled_time.timestamp()
                    self.task_queue.put((execution_time, timeout_processing, task_name, task_id, func, args, kwargs))
                except ValueError:
                    # If task_name is not a valid time string, do not reschedule
                    logger.warning(
                        f"Timer task | {task_id} | task_name is not a valid time string, not rescheduling")

            # Check if all tasks are completed
            with self.lock:
                if self.task_queue.empty() and len(self.running_tasks) == 0:
                    self._reset_idle_timer()

    # The task scheduler closes the countdown
    def _reset_idle_timer(self) -> None:
        """
        Reset the idle timer.
        """
        with self.idle_timer_lock:
            if self.idle_timer is not None:
                self.idle_timer.cancel()
            self.idle_timer = threading.Timer(self.idle_timeout, self.stop_scheduler, args=(False, True,))
            self.idle_timer.start()

    def _cancel_idle_timer(self) -> None:
        """
        Cancel the idle timer.
        """
        with self.idle_timer_lock:
            if self.idle_timer is not None:
                self.idle_timer.cancel()
                self.idle_timer = None

    def _clear_task_queue(self) -> None:
        """
        Clear the task queue.
        """
        while not self.task_queue.empty():
            self.task_queue.get(timeout=1)

    def _join_scheduler_thread(self) -> None:
        """
        Wait for the scheduler thread to finish.
        """
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join()

    def force_stop_task(self,
                        task_id: str) -> bool:
        """
        Force stop a task by its task ID.

        :param task_id: Task ID.

        :return: bool: Whether the task was successfully force stopped.
        """
        if not task_manager.check(task_id):
            logger.warning(f"Timer task | {task_id} | does not exist or is already completed")
            return False

        task_manager.skip_task(task_id)

        task_status_manager.add_task_status(task_id, None, "cancelled", None, None, None, None)
        with self.lock:
            if task_id in self.task_results:
                del self.task_results[task_id]
        return True

    # Obtain the information returned by the corresponding task
    def get_task_result(self,
                        task_id: str) -> Optional[Any]:
        """
        Get the result of a task. If there is a result, return and delete the oldest result; if no result, return None.

        :param task_id: Task ID.

        :return: Optional[Any]: Task return result, or None if the task is not completed or does not exist.
        """
        if task_id in self.task_results:
            result = self.task_results[task_id]
            with self.lock:
                del self.task_results[task_id]
            return result
        return None
