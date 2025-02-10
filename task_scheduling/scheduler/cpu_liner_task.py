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

    except StopException:
        logger.info(f"Cpu linear task | {task_id} | cancelled, forced termination")
        task_status_queue.put(("cancelled", task_id, None, None, None, None, None))
        return_results = "error happened"

    except KeyboardInterrupt:
        pass

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
        'task_queue', 'running_tasks',
        'lock', 'condition', 'scheduler_lock',
        'scheduler_started', 'scheduler_stop_event', 'scheduler_thread',
        'idle_timer', 'idle_timeout', 'idle_timer_lock',
        'task_results',
        'manager', 'task_status_queue',
        'executor', 'status_thread'
    ]

    def __init__(self) -> None:
        """
        Initialize the CpuLinerTask manager.
        """
        self.task_queue = queue.Queue()  # Task queue
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

        self.task_results: Dict[str, Any] = {}  # Store task return results, keep up to 2 results for each task ID

        self.manager = Manager()
        self.task_status_queue = self.manager.Queue()  # Queue for task status updates

        self.executor: Optional[ProcessPoolExecutor] = None

        # Start a thread to handle task status updates
        self.status_thread = threading.Thread(target=self._handle_task_status_updates, daemon=True)

    def _handle_task_status_updates(self) -> None:
        """
        Handle task status updates from the task status queue.
        """
        while not self.scheduler_stop_event.is_set() or not self.task_status_queue.empty():
            try:
                if not self.task_status_queue.empty():
                    task = self.task_status_queue.get(timeout=1.0)
                    if isinstance(task, tuple):
                        status, task_id, task_name, start_time, end_time, error, timeout_processing = task
                        task_status_manager.add_task_status(task_id, task_name, status, start_time, end_time, error,
                                                            timeout_processing)
                    else:
                        self.task_status_queue.put(task)
            except queue.Empty:
                continue
            except EOFError:
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
            with self.scheduler_lock:
                if self.task_queue.qsize() >= config["cpu_liner_task"]:
                    logger.warning(f"Cpu linear task | {task_id} | not added, queue is full")
                    return False

                if task_name in [details[1] for details in self.running_tasks.values()]:
                    logger.warning(f"Cpu linear task | {task_id} | not added, task name already running")
                    return False

                if self.scheduler_stop_event.is_set() and not self.scheduler_started:
                    self._join_scheduler_thread()

                # Reduce the granularity of the lock
                self.task_status_queue.put(("waiting", task_id, None, None, None, None, None))

                self.task_queue.put((timeout_processing, task_name, task_id, func, args, kwargs))

                if not self.scheduler_started:
                    self._start_scheduler()

                with self.condition:
                    self.condition.notify()

                self._cancel_idle_timer()

                return True
        except Exception as e:
            logger.error(f"Cpu linear task | {task_id} | error adding task: {e}")
            return False

    def _start_scheduler(self) -> None:
        """
        Start the scheduler thread.
        """
        self.scheduler_started = True
        self.scheduler_thread = threading.Thread(target=self._scheduler, daemon=True)
        self.scheduler_thread.start()
        self.status_thread.start()

    def stop_scheduler(self,
                       force_cleanup: bool,
                       system_operations: bool = False) -> None:
        """
        Stop the scheduler thread.

        :param force_cleanup: If True, force stop all tasks and clear the queue.
                              If False, gracefully stop the scheduler (e.g., due to idle timeout).
        :param system_operations: Boolean indicating if this stop is due to system operations.
        """
        with self.scheduler_lock:
            # Check if there are any running tasks
            if not self.task_queue.empty() or not len(self.running_tasks) == 0:
                if system_operations:
                    logger.warning(f"Cpu liner task | detected running tasks | stopping operation terminated")
                    return None

            if force_cleanup:
                logger.warning("Force stopping scheduler and cleaning up tasks")
                # Ensure the executor is properly shut down
                if self.executor:
                    self.executor.shutdown(wait=False)
                # Wait for all running tasks to complete
                self.scheduler_stop_event.set()
            else:
                # Ensure the executor is properly shut down
                if self.executor:
                    self.executor.shutdown(wait=True)
                # Wait for all running tasks to complete
                self.scheduler_stop_event.set()

            # Clear the task queue
            self._clear_task_queue()

            # Notify all waiting threads
            with self.condition:
                self.condition.notify_all()

            # Wait for the scheduler thread to finish
            self._join_scheduler_thread()
            self.status_thread.join()

            # Ensure the manager is properly shut down
            self.manager.shutdown()

            # Reset state variables
            self.scheduler_started = False
            self.scheduler_stop_event.clear()
            self.scheduler_thread = None
            self.idle_timer = None
            self.task_results = {}

            logger.info(
                "Scheduler and event loop have stopped, all resources have been released and parameters reset")

    def _scheduler(self) -> None:
        """
        Scheduler function, fetch tasks from the task queue and submit them to the process pool for execution.
        """
        with ProcessPoolExecutor(max_workers=int(config["io_liner_task"])) as executor:
            self.executor = executor
            while not self.scheduler_stop_event.is_set():
                with self.condition:
                    while self.task_queue.empty() and not self.scheduler_stop_event.is_set():
                        self.condition.wait()

                    if self.scheduler_stop_event.is_set():
                        break

                    if self.task_queue.qsize() == 0:
                        continue

                    task = self.task_queue.get()

                timeout_processing, task_name, task_id, func, args, kwargs = task
                with self.lock:
                    future = executor.submit(_execute_task, task, self.task_status_queue)
                    self.running_tasks[task_id] = [future, task_name]
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
                    with self.lock:
                        self.task_results[task_id] = result

        except Exception as e:
            logger.error(f"Cpu linear task | {task_id} | execution failed in callback: {e}")
            self.task_status_queue.put(("failed", task_id, None, None, None, e, None))
        finally:
            # Make sure the Future object is deleted
            with self.lock:
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]

                if self.task_queue.empty() and len(self.running_tasks) == 0:
                    self._reset_idle_timer()

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
        if self.running_tasks.get(task_id) is None:
            logger.warning(f"Cpu linear task | {task_id} | does not exist or is already completed")
            return False

        self.task_status_queue.put(("cancelled", task_id, None, None, None, None, None))
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
            with self.lock:
                result = self.task_results[task_id]  # Return and delete the oldest result
                del self.task_results[task_id]
                return result
        return None
