# -*- coding: utf-8 -*-
import queue
import threading
import time
from concurrent.futures import ProcessPoolExecutor, Future
from functools import partial
from multiprocessing import Event, Lock, RLock, Condition
from typing import Callable, Dict, List, Tuple, Optional, Any

from task_scheduling.manager.task_details_queue import task_status_manager
from ..common import logger
from ..config import config


class CpuLinerTask:
    """
    Linear task manager class, responsible for managing the scheduling, execution, and monitoring of linear tasks.
    """
    __slots__ = [
        'task_queue', 'running_tasks', 'lock', 'condition', 'scheduler_lock',
        'scheduler_started', 'scheduler_stop_event', 'scheduler_thread',
        'idle_timer', 'idle_timeout', 'idle_timer_lock', 'task_results'
    ]

    def __init__(self) -> None:
        self.task_queue = queue.Queue()  # Task queue
        self.running_tasks = {}  # Running tasks
        self.lock = Lock()  # Lock to protect access to shared resources
        self.scheduler_lock = RLock()  # Thread unlock

        self.condition = Condition()  # Condition variable for thread synchronization
        self.scheduler_started = False  # Whether the scheduler thread has started
        self.scheduler_stop_event = Event()  # Scheduler thread stop event
        self.scheduler_thread: Optional[threading.Thread] = None  # Scheduler thread
        self.idle_timer: Optional[threading.Timer] = None  # Idle timer
        self.idle_timeout = config["max_idle_time"]  # Idle timeout, default is 60 seconds
        self.idle_timer_lock = Lock()  # Idle timer lock
        self.task_results: Dict[str, List[Any]] = {}  # Store task return results, keep up to 2 results for each task ID

    # Add the task to the scheduler
    def add_task(self, timeout_processing: bool, task_name: str, task_id: str, func: Callable, *args, **kwargs) -> bool:
        try:
            with self.scheduler_lock:

                if self.task_queue.qsize() >= config["maximum_queue_line"]:
                    logger.warning(f"Cpu linear task | {task_id} | not added, queue is full")
                    return False

                if self.scheduler_stop_event.is_set() and not self.scheduler_started:
                    self._join_scheduler_thread()
                    logger.info("Scheduler has fully stopped")

                # Reduce the granularity of the lock
                task_status_manager.add_task_status(task_id, task_name, "pending", None, None, None,
                                                    timeout_processing)

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
                    logger.warning(f"Cpu linear task | detected running tasks | stopping operation terminated")
                    return None

            logger.warning("Exit cleanup")
            if force_cleanup:
                logger.warning("Force stopping scheduler and cleaning up tasks")
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

    # Task scheduler
    def _scheduler(self) -> None:
        """
        Scheduler function, fetch tasks from the task queue and submit them to the process pool for execution.
        """
        with ProcessPoolExecutor(max_workers=int(config["line_task_max"])) as executor:
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
                    if task_name in [details[1] for details in self.running_tasks.values()]:
                        self.task_queue.put(task)
                        continue

                    future = executor.submit(self._execute_task, task)
                    self.running_tasks[task_id] = [future, task_name]

                future.add_done_callback(partial(self._task_done, task_id))

    # A function that executes a task
    def _execute_task(self, task: Tuple[bool, str, str, Callable, Tuple, Dict]) -> Any:
        timeout_processing, task_name, task_id, func, args, kwargs = task

        return_results = None
        try:
            task_status_manager.add_task_status(task_id, task_name, "running", time.time(), None, None,
                                                timeout_processing)

            logger.info(f"Start running cpu linear task, task ID: {task_id}")
            if timeout_processing:
                return_results = self._run_with_timeout(func, args, kwargs, config["watch_dog_time"])
            else:
                return_results = func(*args, **kwargs)
        except TimeoutError:
            logger.warning(f"Cpu linear task | {task_id} | timed out, forced termination")
            task_status_manager.add_task_status(task_id, task_name, "timeout", None, None, None,
                                                timeout_processing)
        except Exception as e:
            logger.error(f"Cpu linear task | {task_id} | execution failed: {e}")
            task_status_manager.add_task_status(task_id, task_name, "failed", None, None, e,
                                                timeout_processing)
        finally:
            if return_results is None:
                return_results = "error happened"
            return return_results

    def _run_with_timeout(self, func: Callable, args: Tuple, kwargs: Dict, timeout: int) -> Any:
        """
        Run a function with a timeout.

        :param func: The function to run.
        :param args: Positional arguments for the function.
        :param kwargs: Keyword arguments for the function.
        :param timeout: Timeout in seconds.
        :return: The result of the function or None if it times out.
        """

        def target(result_queue):
            try:
                result_queue.put(func(*args, **kwargs))
            except Exception as e:
                result_queue.put(e)

        result_queue = queue.Queue()
        process = threading.Thread(target=target, args=(result_queue,))
        process.start()
        process.join(timeout=timeout)

        if process.is_alive():
            raise TimeoutError("Task timed out")
        else:
            result = result_queue.get()
            if isinstance(result, Exception):
                raise result
            return result

    def _task_done(self, task_id: str, future: Future) -> None:
        """
        Callback function after a task is completed.

        :param task_id: Task ID.
        :param future: Future object corresponding to the task.
        """
        try:
            result = future.result()  # Get task result, exceptions will be raised here

            # Store task return results, keep up to 2 results
            with self.lock:
                if task_id not in self.task_results:
                    self.task_results[task_id] = []
                self.task_results[task_id].append(result)
                if len(self.task_results[task_id]) > 2:
                    self.task_results[task_id].pop(0)  # Remove the oldest result
            if not result == "error happened":
                task_status_manager.add_task_status(task_id, None, "completed", None, time.time(), None, None)
        finally:
            # Ensure the Future object is deleted
            with self.lock:
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]

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
        with self.lock:
            if task_id not in self.running_tasks:
                logger.warning(f"Cpu linear task | {task_id} | does not exist or is already completed")
                return False

        task_status_manager.add_task_status(task_id, None, "cancelled", None, None, None, None)
        with self.lock:
            if task_id in self.task_results:
                del self.task_results[task_id]
        return True

    def cancel_all_queued_tasks_by_name(self, task_name: str) -> None:
        """
        Cancel all queued tasks with the same name.

        :param task_name: Task name.
        """
        with self.condition:
            temp_queue = queue.Queue()
            while not self.task_queue.empty():
                task = self.task_queue.get()
                if task[1] == task_name:  # Use function name to match task name
                    logger.warning(
                        f"Cpu linear taskCpu linear task | {task_name} | is waiting to be executed in the queue, has been deleted")
                else:
                    temp_queue.put(task)

            # Put uncancelled tasks back into the queue
            while not temp_queue.empty():
                self.task_queue.put(temp_queue.get())

    # Obtain the information returned by the corresponding task
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """
        Get the result of a task. If there is a result, return and delete the oldest result; if no result, return None.

        :param task_id: Task ID.
        :return: Task return result, if the task is not completed or does not exist, return None.
        """
        if task_id in self.task_results and self.task_results[task_id]:
            result = self.task_results[task_id].pop(0)  # Return and delete the oldest result
            with self.lock:
                if not self.task_results[task_id]:
                    del self.task_results[task_id]
            return result
        return None


cpu_liner_task = CpuLinerTask()
