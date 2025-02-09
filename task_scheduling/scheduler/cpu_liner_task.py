import queue
import threading
import time
from concurrent.futures import ProcessPoolExecutor, Future
from functools import partial
from multiprocessing import Manager, TimeoutError
from typing import Callable, Dict, Tuple, Optional, Any

from ..common import logger
from ..config import config
from ..manager import task_status_manager
from ..stopit import TaskManager

# Create Manager instance
task_manager = TaskManager()


def _execute_task(task: Tuple[bool, str, str, Callable, Tuple, Dict], task_status_queue: queue.Queue) -> Any:
    timeout_processing, task_name, task_id, func, args, kwargs = task

    return_results = None
    try:
        task_status_queue.put(("running", task_id, task_name, time.time(), None, None, timeout_processing))

        logger.info(f"Start running cpu linear task, task ID: {task_id}")
        if timeout_processing:
            return_results = func(*args, **kwargs)
        else:
            return_results = func(*args, **kwargs)
    except TimeoutError:
        logger.warning(f"Cpu linear task | {task_id} | timed out, forced termination")
        task_status_queue.put(("timeout", task_id, task_name, None, None, None, timeout_processing))
        return_results = "error happened"
    except Exception as e:
        logger.error(f"Cpu linear task | {task_id} | execution failed: {e}")
        task_status_queue.put(("failed", task_id, task_name, None, None, e, timeout_processing))
        return_results = "error happened"
    finally:
        task_status_queue.put(("completed", task_id, task_name, None, time.time(), None, timeout_processing))
        return return_results


class CpuLinerTask:
    """
    Linear task manager class, responsible for managing the scheduling, execution, and monitoring of linear tasks.
    """
    __slots__ = [
        'task_queue', 'running_tasks', 'lock', 'condition', 'scheduler_lock',
        'scheduler_started', 'scheduler_stop_event', 'scheduler_thread',
        'idle_timer', 'idle_timeout', 'idle_timer_lock', 'task_results',
        'task_status_queue', 'status_thread'
    ]

    def __init__(self) -> None:
        manager = Manager()

        self.task_queue = queue.Queue()  # Task queue
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
        self.task_results: Dict[str, Any] = {}  # Store task return results, keep up to 2 results for each task ID
        self.task_status_queue = manager.Queue()  # Queue for task status updates

        # Start a thread to handle task status updates
        self.status_thread = threading.Thread(target=self._handle_task_status_updates, daemon=True)

    # Handle task status updates from the task status queue
    def _handle_task_status_updates(self) -> None:
        while not self.scheduler_stop_event.is_set():
            try:
                if not self.task_status_queue.empty():
                    status, task_id, task_name, start_time, end_time, error, timeout_processing = self.task_status_queue.get(
                        timeout=1)
                    task_status_manager.add_task_status(task_id, task_name, status, start_time, end_time, error,
                                                        timeout_processing)
            finally:
                continue

    # Add the task to the scheduler
    def add_task(self, timeout_processing: bool, task_name: str, task_id: str, func: Callable, *args, **kwargs) -> bool:
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
                self.task_status_queue.put(("waiting", task_id, task_name, None, None, None, timeout_processing))

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

    # Start the scheduler
    def _start_scheduler(self) -> None:
        """
        Start the scheduler thread.
        """
        self.scheduler_started = True
        self.scheduler_thread = threading.Thread(target=self._scheduler, daemon=True)
        self.scheduler_thread.start()
        self.status_thread.start()

    def stop_scheduler(self, force_cleanup: bool, system_operations: bool = False) -> None:
        """
        Stop the scheduler thread.

        :param force_cleanup: If True, force stop all tasks and clear the queue.
                              If False, gracefully stop the scheduler (e.g., due to idle timeout).
        :param system_operations: System execution metrics
        """

        with self.scheduler_lock:
            # Check if there are any running tasks
            if not self.task_queue.empty() or not len(self.running_tasks) == 0:
                if system_operations:
                    logger.warning(f"Cpu liner task | detected running tasks | stopping operation terminated")
                    return None

            if force_cleanup:
                logger.warning("Force stopping scheduler and cleaning up tasks")
                task_manager.terminate_all_tasks()
                self.scheduler_stop_event.set()
            else:
                # Wait for all running tasks to complete
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

    # Task scheduler
    def _scheduler(self) -> None:
        """
        Scheduler function, fetch tasks from the task queue and submit them to the process pool for execution.
        """
        with ProcessPoolExecutor(max_workers=int(config["io_liner_task"])) as executor:
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
                    process = next(iter(executor._processes.values()))

                    task_manager.add(None, None, process, task_id)
                    self.running_tasks[task_id] = [future, task_name, process]

                    future.add_done_callback(partial(self._task_done, task_id))

            # Ensure the executor is properly shut down
            executor.shutdown(wait=False)

    # A function that executes a task
    def _task_done(self, task_id: str, future: Future) -> None:
        """
        Callback function after a task is completed.

        :param task_id: Task ID.
        :param future: Future object corresponding to the task.
        """
        try:
            result = future.result()  # Get the task result, where the exception will be thrown

            # The storage task returns a result, and a maximum of two results are retained
            if result is not None:
                if not result == "error happened":
                    with self.lock:
                        self.task_results[task_id] = result

        except Exception as e:
            logger.error(f"Cpu linear task | {task_id} | execution failed in callback: {e}")
            self.task_status_queue.put(("failed", task_id, None, None, time.time(), e, None))
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

    def force_stop_task(self, task_id: str) -> bool:
        """
        Force stop a task by its task ID.

        :param task_id: task ID
        """

        if not task_manager.check(task_id):
            logger.warning(f"Cpu linear task | {task_id} | does not exist or is already completed")
            return False

        task_manager.terminate_task(task_id)

        self.task_status_queue.put(("cancelled", task_id, None, None, None, None, None))
        with self.lock:
            if task_id in self.task_results:
                del self.task_results[task_id]
        return True

    # Obtain the information returned by the corresponding task
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """
        Get the result of a task. If there is a result, return and delete the oldest result; if no result, return None.

        :param task_id: Task ID.
        :return: Task return result, if the task is not completed or does not exist, return None.
        """
        if task_id in self.task_results:
            with self.lock:
                result = self.task_results[task_id]  # Return and delete the oldest result
                del self.task_results[task_id]
                return result
        return None
