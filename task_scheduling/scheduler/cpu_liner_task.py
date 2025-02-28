# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import queue
import threading
import time
from concurrent.futures import ProcessPoolExecutor, Future
from functools import partial
from multiprocessing import Manager
from typing import Callable, Dict, Tuple, Optional, Any

from ..common import logger
from ..config import config
from ..manager import task_status_manager
from ..stopit import skip_on_demand, ProcessTaskManager, StopException, ThreadingTimeout, TimeoutException
from ..utils import worker_initializer_liner


def _execute_task(task: Tuple[bool, str, str, Callable, Tuple, Dict],
                  task_status_queue: queue.Queue) -> Any:
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
        task_status_queue (queue.Queue): Queue to update task status.

    Returns:
        Any: Result of the task execution or error message.
    """

    timeout_processing, task_name, task_id, func, args, kwargs = task
    task_manager = ProcessTaskManager(task_status_queue)
    return_results = None

    try:
        with skip_on_demand() as skip_ctx:
            task_manager.add(skip_ctx, task_id)

            task_status_queue.put(("running", task_id, None, time.time(), None, None, None))
            logger.info(f"Start running cpu linear task, task ID: {task_id}")
            if timeout_processing:
                with ThreadingTimeout(seconds=config["watch_dog_time"], swallow_exc=False):
                    # Whether to pass in the task manager to facilitate other thread management
                    if config["thread_management"]:
                        return_results = func(task_manager, *args, **kwargs)
                    else:
                        return_results = func(*args, **kwargs)
            else:
                return_results = func(*args, **kwargs)

    except (StopException, KeyboardInterrupt):
        logger.info(f"Cpu linear task | {task_id} | cancelled, forced termination")
        task_status_queue.put(("cancelled", task_id, None, None, None, None, None))
        return_results = "error happened"

    except TimeoutException:
        logger.warning(f"Cpu linear task | {task_id} | timed out, forced termination")
        task_status_queue.put(("timeout", task_id, None, None, None, None, None))
        return_results = "error happened"

    except Exception as e:
        logger.error(f"Cpu linear task | {task_id} | execution failed: {e}")
        task_status_queue.put(("failed", task_id, None, None, None, e, None))
        return_results = "error happened"

    finally:
        if return_results != "error happened":
            try:
                task_status_queue.put(("completed", task_id, None, None, time.time(), None, None))
            except BrokenPipeError:
                pass
        task_manager.remove(task_id)

        return return_results


class CpuLinerTask:
    """
    Linear task manager class, responsible for managing the scheduling, execution, and monitoring of linear tasks.
    """
    __slots__ = [
        '_task_queue', '_running_tasks',
        '_lock', '_condition', '_scheduler_lock',
        '_scheduler_started', '_scheduler_stop_event', '_scheduler_thread',
        '_idle_timer', '_idle_timeout', '_idle_timer_lock',
        '_task_results',
        '_manager', '_task_status_queue',
        '_executor', '_status_thread'
    ]

    def __init__(self) -> None:
        """
        Initialize the CpuLinerTask manager.
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

        self._manager = Manager()
        self._task_status_queue = self._manager.Queue()  # Queue for task status updates

        self._executor: Optional[ProcessPoolExecutor] = None

        # Start a thread to handle task status updates
        self._status_thread = threading.Thread(target=self._handle_task_status_updates, daemon=True)

    def _handle_task_status_updates(self) -> None:
        """
        Handle task status updates from the task status queue.
        """
        while not self._scheduler_stop_event.is_set() or not self._task_status_queue.empty():
            try:
                if not self._task_status_queue.empty():
                    task = self._task_status_queue.get(timeout=1.0)
                    if isinstance(task, tuple):
                        status, task_id, task_name, start_time, end_time, error, timeout_processing = task
                        task_status_manager.add_task_status(task_id, task_name, status, start_time, end_time, error,
                                                            timeout_processing)
                    else:
                        self._task_status_queue.put(task)
            except Exception:
                continue

    def add_task(self,
                 timeout_processing: bool,
                 task_name: str,
                 task_id: str,
                 func: Callable,
                 *args, **kwargs) -> bool:
        """
        Add the task to the scheduler.

        Args:
            timeout_processing (bool): Whether timeout processing is enabled.
            task_name (str): Task name.
            task_id (str): Task ID.
            func (Callable): The function to execute.
            *args: Arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            bool: Whether the task was successfully added.
        """
        try:
            with self._scheduler_lock:
                if self._task_queue.qsize() >= config["cpu_liner_task"]:
                    return False

                if task_name in [details[1] for details in self._running_tasks.values()]:
                    return False

                if self._scheduler_stop_event.is_set() and not self._scheduler_started:
                    self._join_scheduler_thread()

                # Reduce the granularity of the lock
                self._task_status_queue.put(("waiting", task_id, None, None, None, None, None))

                self._task_queue.put((timeout_processing, task_name, task_id, func, args, kwargs))

                if not self._scheduler_started:
                    self._start_scheduler()

                with self._condition:
                    self._condition.notify()

                self._cancel_idle_timer()

                return True
        except Exception as e:
            logger.error(f"Cpu linear task | {task_id} | error adding task: {e}")
            return False

    def _start_scheduler(self) -> None:
        """
        Start the scheduler thread.
        """
        self._scheduler_started = True
        self._scheduler_thread = threading.Thread(target=self._scheduler, daemon=True)
        self._scheduler_thread.start()
        self._status_thread.start()

    def stop_scheduler(self,
                       force_cleanup: bool,
                       system_operations: bool = False) -> None:
        """
        Stop the scheduler thread.

        :param force_cleanup: If True, force stop all tasks and clear the queue.
                              If False, gracefully stop the scheduler (e.g., due to idle timeout).
        :param system_operations: Boolean indicating if this stop is due to system operations.
        """
        with self._scheduler_lock:
            # Check if there are any running tasks
            if not self._task_queue.empty() or not len(self._running_tasks) == 0:
                if system_operations:
                    logger.warning(f"Cpu liner task | detected running tasks | stopping operation terminated")
                    return None

            if force_cleanup:
                logger.warning("Force stopping scheduler and cleaning up tasks")
                self.stop_all_running_task()
                # Ensure the executor is properly shut down
                if self._executor:
                    self._executor.shutdown(wait=False, cancel_futures=True)
            else:
                # Ensure the executor is properly shut down
                if self._executor:
                    self._executor.shutdown(wait=True, cancel_futures=True)

            # Wait for all running tasks to complete
            self._scheduler_stop_event.set()

            # Clear the task queue
            self._clear_task_queue()

            # Notify all waiting threads
            with self._condition:
                self._condition.notify_all()

            # Wait for the scheduler thread to finish
            self._join_scheduler_thread()
            self._status_thread.join()

            # Ensure the manager is properly shut down
            self._manager.shutdown()

            # Reset state variables
            self._scheduler_started = False
            self._scheduler_stop_event.clear()
            self._scheduler_thread = None
            self._idle_timer = None
            self._task_results = {}

            # logger.info(
            #     "Scheduler and event loop have stopped, all resources have been released and parameters reset")

    def stop_all_running_task(self):
        for task_id in self._running_tasks.keys():
            self._task_status_queue.put(task_id)

        while not self._task_status_queue.qsize() == 0:
            time.sleep(0.1)

    def _scheduler(self) -> None:
        """
        Scheduler function, fetch tasks from the task queue and submit them to the process pool for execution.
        """
        with ProcessPoolExecutor(max_workers=int(config["cpu_liner_task"]),
                                 initializer=worker_initializer_liner) as executor:
            self._executor = executor
            while not self._scheduler_stop_event.is_set():
                with self._condition:
                    while self._task_queue.empty() and not self._scheduler_stop_event.is_set():
                        self._condition.wait()

                    if self._scheduler_stop_event.is_set():
                        break

                    if self._task_queue.qsize() == 0:
                        continue

                    task = self._task_queue.get()

                timeout_processing, task_name, task_id, func, args, kwargs = task
                with self._lock:
                    future = executor.submit(_execute_task, task, self._task_status_queue)
                    self._running_tasks[task_id] = [future, task_name]
                    future.add_done_callback(partial(self._task_done, task_id))

    def _task_done(self,
                   task_id: str,
                   future: Future) -> None:
        """
        Callback function after a task is completed.

        :param task_id: Task ID.
        :param future: Future object corresponding to the task.
        """
        try:
            result = future.result()  # Get the task result, where the exception will be thrown
            # The storage task returns a result, and a maximum of two results are retained
            if result is not None:
                if result != "error happened":
                    with self._lock:
                        self._task_results[task_id] = result

        except Exception as e:
            logger.error(f"Cpu linear task | {task_id} | execution failed in callback: {e}")
            self._task_status_queue.put(("failed", task_id, None, None, None, e, None))
        finally:
            # Make sure the Future object is deleted
            with self._lock:
                if task_id in self._running_tasks:
                    del self._running_tasks[task_id]

                if self._task_queue.empty() and len(self._running_tasks) == 0:
                    self._reset_idle_timer()

    def _reset_idle_timer(self) -> None:
        """
        Reset the idle timer.
        """
        with self._idle_timer_lock:
            if self._idle_timer is not None:
                self._idle_timer.cancel()
            self._idle_timer = threading.Timer(self._idle_timeout, self.stop_scheduler, args=(False, True,))
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
                        task_id: str,
                        built_in_task: bool) -> bool:
        """
        Force stop a task by its task ID.

        :param task_id: Task ID.
        :param built_in_task: Built-in task metrics are used for skip detection.

        :return: bool: Whether the task was successfully force stopped.
        """
        if self._running_tasks.get(task_id) is None and built_in_task:
            logger.warning(f"Cpu linear task | {task_id} | does not exist or is already completed")
            return False

        self._task_status_queue.put(task_id)

        self._task_status_queue.put(("cancelled", task_id, None, None, None, None, None))
        with self._lock:
            if task_id in self._task_results:
                del self._task_results[task_id]

        return True

    # Obtain the information returned by the corresponding task
    def get_task_result(self,
                        task_id: str) -> Optional[Any]:
        """
        Get the result of a task. If there is a result, return and delete the oldest result; if no result, return None.

        :param task_id: Task ID.

        :return: Optional[Any]: Task return result, or None if the task is not completed or does not exist.
        """
        if task_id in self._task_results:
            with self._lock:
                result = self._task_results[task_id]  # Return and delete the oldest result
                del self._task_results[task_id]
                return result
        return None
