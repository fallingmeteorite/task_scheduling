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
from ..stopit import TaskManager, skip_on_demand, StopException, ThreadingTimeout, TimeoutException

# Create Manager instance
task_manager = TaskManager()


def _execute_task(task: Tuple[bool, str, str, Callable, Tuple, Dict]) -> Any:
    timeout_processing, task_name, task_id, func, args, kwargs = task

    return_results = None
    try:
        task_status_manager.add_task_status(task_id, task_name, "running", time.time(), None, None,
                                            timeout_processing)

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
        task_status_manager.add_task_status(task_id, task_name, "timeout", None, None, None,
                                            timeout_processing)
        return_results = "error happened"
    except StopException:
        logger.warning(f"Timer task | {task_id} | was cancelled")
        task_status_manager.add_task_status(task_id, task_name, "cancelled", None, None, None,
                                            timeout_processing)
        return_results = "error happened"
    except Exception as e:
        logger.error(f"Timer task | {task_id} | execution failed: {e}")
        task_status_manager.add_task_status(task_id, task_name, "failed", None, None, e,
                                            timeout_processing)
        return_results = "error happened"
    finally:
        if task_manager.check(task_id):
            task_manager.remove(task_id)
        return return_results


class TimerTask:
    """
    Linear task manager class, responsible for managing the scheduling, execution, and monitoring of linear tasks.
    """
    __slots__ = [
        'task_queue', 'running_tasks', 'lock', 'condition', 'scheduler_lock',
        'scheduler_started', 'scheduler_stop_event', 'scheduler_thread',
        'idle_timer', 'idle_timeout', 'idle_timer_lock', 'task_results'
    ]

    def __init__(self) -> None:
        self.task_queue = queue.PriorityQueue()  # Task queue with priority based on execution time
        self.running_tasks = {}  # Running tasks
        self.lock = threading.Lock()  # Lock to protect access to shared resources
        self.scheduler_lock = threading.RLock()  # Thread unlock

        self.condition = threading.Condition()  # Condition variable for thread synchronization
        self.scheduler_started = False  # Whether the scheduler thread has started
        self.scheduler_stop_event = threading.Event()  # Scheduler thread stop event
        self.scheduler_thread: Optional[threading.Thread] = None  # Scheduler thread
        self.idle_timer: Optional[threading.Timer] = None  # Idle timer
        self.idle_timeout = config["max_idle_time"]  # Idle timeout, default is 60 seconds
        self.idle_timer_lock = threading.Lock()  # Idle timer lock
        self.task_results: Dict[str, List[Any]] = {}  # Store task return results, keep up to 2 results for each task ID

    # Add the task to the scheduler
    def add_task(self, delay: Optional[int] = None, daily_time: Optional[str] = None,
                 timeout_processing: bool = False, task_name: str = "", task_id: str = "",
                 func: Callable = None, *args, **kwargs) -> bool:
        try:
            with self.scheduler_lock:
                if self.scheduler_stop_event.is_set() and not self.scheduler_started:
                    self._join_scheduler_thread()

                # Reduce the granularity of the lock
                task_status_manager.add_task_status(task_id, task_name, "waiting", None, None, None,
                                                    timeout_processing)

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

                self.task_queue.put((timeout_processing, task_name, task_id, func, execution_time, args, kwargs))

                if not self.scheduler_started:
                    self._start_scheduler()

                with self.condition:
                    self.condition.notify()

                self._cancel_idle_timer()

                return True
        except Exception as e:
            logger.error(f"Timer task | {task_id} | error adding task: {e}")
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
    def stop_scheduler(self, force_cleanup: bool, system_operations: bool = False) -> None:
        """
        Stop the scheduler thread.

        :param force_cleanup: If True, force stop all tasks and clear the queue.
                              If False, gracefully stop the scheduler (e.g., due to idle timeout).
        :param system_operations: System execution metrics
        """
        with self.scheduler_lock:
            # Check if all tasks are completed
            if not self.task_queue.empty() or not len(self.running_tasks) == 0:
                if system_operations:
                    logger.warning(f"Cpu asyncio task was detected to be running, and the task stopped terminating")
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

    # Scheduler function
    def _scheduler(self) -> None:
        """
        Scheduler function, fetch tasks from the task queue and submit them to the thread pool for execution.
        """
        with ThreadPoolExecutor(max_workers=int(config["line_task_max"])) as executor:
            while not self.scheduler_stop_event.is_set():
                with self.condition:
                    while self.task_queue.empty() and not self.scheduler_stop_event.is_set():
                        self.condition.wait()

                    if self.scheduler_stop_event.is_set():
                        break

                    if self.task_queue.qsize() == 0:
                        continue

                    timeout_processing, task_name, task_id, func, execution_time, args, kwargs = self.task_queue.get()

                    if execution_time > time.time():
                        self.task_queue.put(
                            (timeout_processing, task_name, task_id, func, execution_time, args, kwargs))
                        self.condition.wait(execution_time - time.time())
                        continue

                with self.lock:

                    future = executor.submit(_execute_task,
                                             (timeout_processing, task_name, task_id, func, args, kwargs))
                    self.running_tasks[task_id] = [future, task_name]

                future.add_done_callback(
                    partial(self._task_done, task_id, timeout_processing, task_name, task_id, func, args, kwargs))

    # A function that executes a task
    def _task_done(self, task_id: str, timeout_processing: bool, task_name: str, task_id_: str, func: Callable,
                   args: Tuple, kwargs: Dict, future: Future) -> None:
        """
        Callback function after a task is completed.

        :param task_id: Task ID.
        :param future: Future object corresponding to the task.
        """
        try:
            result = future.result()  # Get task result, exceptions will be raised here
            if not result == "error happened":
                task_status_manager.add_task_status(task_id, None, "completed", None, time.time(), None, None)
        finally:
            # Ensure the Future object is deleted
            with self.lock:
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]

            # Check if the task is a daily task and reschedule it for the next day
            if not timeout_processing:
                try:
                    daily_time_obj = datetime.strptime(task_name, "%H:%M")
                    now = datetime.now()
                    scheduled_time = datetime(now.year, now.month, now.day, daily_time_obj.hour, daily_time_obj.minute)
                    if scheduled_time < now:
                        scheduled_time += timedelta(days=1)
                    execution_time = scheduled_time.timestamp()
                    self.task_queue.put((timeout_processing, task_name, task_id_, func, execution_time, args, kwargs))
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

    def force_stop_task(self, task_id: str) -> bool:
        """
        Force stop a task by its task ID.

        :param task_id: task ID.
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
