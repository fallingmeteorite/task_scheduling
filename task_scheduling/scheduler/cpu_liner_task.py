# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""CPU-bound linear task execution module.

This module provides a task scheduler for CPU-bound linear tasks using
process pool execution with priority-based scheduling and timeout handling.
"""
import queue
import os
import threading
import time
import dill

from concurrent.futures import ProcessPoolExecutor, Future, BrokenExecutor
from functools import partial
from typing import Callable, Dict, Tuple, Optional, Any, List
from task_scheduling.common import logger, config
from task_scheduling.control import ProcessTaskManager
from task_scheduling.handling import ThreadTerminator, StopException, ThreadSuspender, TimeoutException, \
    ThreadingTimeout
from task_scheduling.manager import task_status_manager, SharedTaskDict
from task_scheduling.result_server import store_task_result
from task_scheduling.scheduler.utils import exit_cleanup, TaskCounter, SharedStatusInfo, get_param_count, \
    retry_on_error_decorator_check, DillProcessPoolExecutor

_task_counter = TaskCounter("cpu_liner_task")
shared_status_info_liner = SharedStatusInfo()


def _execute_task(task: Tuple[bool, str, str, Callable, str, Tuple, Dict],
                  task_status_queue: queue.Queue,
                  task_signal_transmission: dict,
                  task_pid: dict) -> Any:
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
        task_status_queue: Queue to update task status.
        task_signal_transmission: Dict to transmission signal.
        task_pid: Dict to process task pid.

    Returns:
        Result of the task execution or error message.
    """
    # Get process ID
    timeout_processing, task_name, task_id, func, priority, args, kwargs = task
    logger.debug(f"Start running task, task ID: {task_id}")
    task_pid[task_id] = os.getpid()

    # Create a shared dictionary
    _sharedtaskdict = SharedTaskDict()

    task_manager = ProcessTaskManager(task_signal_transmission)
    try:
        with ThreadTerminator().terminate_control() as terminate_ctx:
            with ThreadSuspender() as pause_ctx:
                task_manager.add(terminate_ctx, pause_ctx, task_id)

                task_status_queue.put(("running", task_id, None, time.time(), None, None, None))

                if timeout_processing:
                    with ThreadingTimeout(seconds=config["watch_dog_time"], swallow_exc=False):
                        # Whether to pass in the task manager to facilitate other thread management
                        # Check whether the function needs to use hyperthreading
                        if get_param_count(func, *args, **kwargs):
                            share_info = (task_name, task_manager, ThreadTerminator, StopException, ThreadingTimeout,
                                          TimeoutException, ThreadSuspender, task_status_queue)
                            if retry_on_error_decorator_check(func):
                                result = func(task_id, share_info, _sharedtaskdict, task_signal_transmission, *args,
                                              **kwargs)
                            else:
                                result = func(share_info, _sharedtaskdict, task_signal_transmission, *args,
                                              **kwargs)
                        else:
                            if retry_on_error_decorator_check(func):
                                result = func(task_id, *args, **kwargs)
                            else:
                                result = func(*args, **kwargs)
                else:
                    # Whether to pass in the task manager to facilitate other thread management
                    # Check whether the function needs to use hyperthreading
                    if get_param_count(func, *args, **kwargs):
                        share_info = (task_name, task_manager, ThreadTerminator, StopException, ThreadingTimeout,
                                      TimeoutException, ThreadSuspender, task_status_queue)
                        if retry_on_error_decorator_check(func):
                            result = func(task_id, share_info, _sharedtaskdict, task_signal_transmission, *args,
                                          **kwargs)
                        else:
                            result = func(share_info, _sharedtaskdict, task_signal_transmission, *args,
                                          **kwargs)
                    else:
                        if retry_on_error_decorator_check(func):
                            result = func(task_id, *args, **kwargs)
                        else:
                            result = func(*args, **kwargs)

    except (StopException, KeyboardInterrupt):
        logger.warning(f"task | {task_id} | cancelled, forced termination")
        task_status_queue.put(("cancelled", task_id, None, None, None, None, None))
        result = "cancelled action"

    except TimeoutException:
        # Terminate all other threads under the main thread
        logger.warning(f"task | {task_id} | timed out, forced termination")
        task_status_queue.put(("timeout", task_id, None, None, None, None, None))
        result = "timeout action"

    except Exception as error:
        if config["exception_thrown"]:
            raise

        logger.error(f"task | {task_id} | execution failed: {error}")
        task_status_queue.put(("failed", task_id, None, None, None, error, None))
        result = "failed action"

    finally:
        # Terminate all other threads under the main thread
        task_manager.terminate_branch_tasks()

        # Remove main thread logging
        if task_manager.exists(task_id):
            task_manager.remove(task_id)

        # Clean up PID mapping
        if task_id in task_pid:
            del task_pid[task_id]

    return result


class CpuLinerTask:
    """
    Linear task manager class, responsible for managing the scheduling, execution, and monitoring of linear tasks.
    """
    __slots__ = [
        '_task_queue', '_running_tasks', '_running_task_names',
        '_lock', '_condition', '_scheduler_lock',
        '_scheduler_started', '_scheduler_stop_event', '_scheduler_thread', '_task_add_lock',
        '_idle_timer', '_idle_timeout', '_idle_timer_lock',
        '_task_results',
        '_executor', '_status_thread'
    ]

    def __init__(self) -> None:
        """
        Initialize the CpuLinerTask manager.
        """
        self._task_queue = queue.Queue()  # Task queue
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

        self._executor: Optional[ProcessPoolExecutor] = None

        # Start a thread to handle task status updates
        self._status_thread = threading.Thread(target=self._handle_task_status_updates, daemon=True)

    def _handle_task_status_updates(self) -> None:
        """
        Handle task status updates from the task status queue.
        """
        while not self._scheduler_stop_event.is_set() or not shared_status_info_liner.task_status_queue.empty():
            try:
                task = shared_status_info_liner.task_status_queue.get(timeout=0.1)
                if len(task) == 7:
                    status, task_id, task_name, start_time, end_time, error, timeout_processing = task
                    priority = None
                else:
                    status, task_id, task_name, start_time, end_time, error, timeout_processing, priority = task
                task_status_manager.add_task_status(task_id, task_name, status, start_time, end_time, error,
                                                    timeout_processing, "cpu_liner_task", priority)

            except (queue.Empty, ValueError, EOFError, BrokenPipeError):
                pass  # Ignore empty queue exceptions

    def add_task(self,
                 timeout_processing: bool,
                 task_name: str,
                 task_id: str,
                 func: Callable,
                 priority: str,
                 *args, **kwargs) -> Any:
        """
        Add the task to the scheduler.

        Args:
            timeout_processing: Whether timeout processing is enabled.
            task_name: Task name.
            task_id: Task ID.
            func: The function to execute.
            priority: Mission importance level.
            *args: Arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            Whether the task was successfully added.
        """
        try:
            while self._task_add_lock:
                time.sleep(0.01)

            need_add_high = False
            # 1. Capacity check (lock only for shared state)
            with self._lock:

                if len(self._running_tasks) >= config[
                    "cpu_liner_task"]:
                    if _task_counter.is_high_priority(priority):
                        if _task_counter.is_high_priority_full(config["cpu_liner_task"]):
                            return False
                        need_add_high = True
                    return False

                if task_name in self._running_task_names:
                    return False

            if need_add_high:
                _task_counter.add_high_priority_task(task_id, self._running_tasks)

            # 2. Status updates (queue is thread-safe)
            shared_status_info_liner.task_status_queue.put(("waiting", task_id, None, None, None, None, None))

            # 3. Put task into queue (thread-safe)
            self._task_queue.put((timeout_processing, task_name, task_id, func, priority, args, kwargs))
            with self._lock:
                self._task_add_lock = True

            # 4. Start scheduler if needed (only protect start flag)
            with self._scheduler_lock:
                if not self._scheduler_started:
                    self._start_scheduler()

            # 5. Notify scheduler (condition lock held only for notify)
            with self._condition:
                self._condition.notify()

            # 6. Cancel idle timer (has its own lock)
            self._cancel_idle_timer()

            return True
        except Exception as error:
            return error

    def _start_scheduler(self) -> None:
        """
        Start the scheduler thread.
        """
        self._scheduler_started = True
        self._scheduler_stop_event.clear()
        self._scheduler_thread = threading.Thread(target=self._scheduler, daemon=True)
        self._scheduler_thread.start()
        self._status_thread.start()

    def stop_scheduler(self,
                       system_operations: bool = False) -> None:
        """
        Stop the scheduler thread.

        Args:
            system_operations: Boolean indicating if this stop is due to system operations.
        """
        # Set stop event and notify all waiting threads
        self._scheduler_stop_event.set()

        with self._condition:
            self._condition.notify_all()

        with self._scheduler_lock:
            # Check if there are any running tasks (only when system_operations)
            if system_operations:
                with self._lock:
                    queue_empty = self._task_queue.empty()
                    running_tasks_empty = len(self._running_tasks) == 0
                    if not queue_empty or not running_tasks_empty:
                        logger.warning(f"Cpu liner task | detected running tasks | stopping operation terminated")
                        return None

            # Resume all paused tasks (lock only for accessing _running_tasks)
            with self._lock:
                for task_id, _ in self._running_tasks.items():
                    shared_status_info_liner.task_signal_transmission[task_id] = ["resume", "kill"]

            # Shutdown executor (no lock needed)
            if self._executor:
                self._executor.shutdown(wait=False, cancel_futures=True)

            # Clear task queue
            self._clear_task_queue()

            # Wait for scheduler thread to finish
            self._join_scheduler_thread()

            # Wait for status thread
            if self._status_thread.is_alive():
                self._status_thread.join(timeout=1.0)
            self._status_thread = threading.Thread(target=self._handle_task_status_updates, daemon=True)

            # Wait for running tasks to finish
            self._wait_tasks_end()

            # Reset state (lock only for resetting shared variables)
            with self._lock:
                self._scheduler_started = False
                self._running_tasks.clear()
                self._running_task_names.clear()
                self._task_results.clear()
                self._task_add_lock = False

            self._scheduler_thread = None

            # Cancel idle timer (has its own lock)
            with self._idle_timer_lock:
                if self._idle_timer is not None:
                    self._idle_timer.cancel()
                    self._idle_timer = None

            logger.debug("Scheduler and event loop have stopped, all resources have been released and parameters reset")
        return None

    def _wait_tasks_end(self) -> None:
        """
        Wait for all tasks to finish
        """
        while True:
            if len(self._running_tasks) == 0:
                break
            time.sleep(0.01)

    def _scheduler(self) -> None:
        """
        Scheduler function, fetch tasks from the task queue and submit them to the process pool for execution.
        """
        with DillProcessPoolExecutor(
                max_workers=int(config["cpu_liner_task"] * 2),
                initializer=exit_cleanup) as executor:

            self._executor = executor
            while not self._scheduler_stop_event.is_set():
                task = None
                # Wait for task with condition, but release lock before submitting
                with self._condition:
                    while (self._task_queue.empty() and
                           not self._scheduler_stop_event.is_set()):
                        self._condition.wait(timeout=1.0)

                    if self._scheduler_stop_event.is_set():
                        break

                    if self._task_queue.empty():
                        continue

                    # Atomically get a task from the queue (inside lock)
                    task = self._task_queue.get()

                # Now task is taken out of queue, lock released
                if task is None:
                    continue

                timeout_processing, task_name, task_id, func, priority, args, kwargs = task

                # Submit to executor (no lock held)
                try:
                    future = executor.submit(_execute_task, task, shared_status_info_liner.task_status_queue,
                                             shared_status_info_liner.task_signal_transmission,
                                             shared_status_info_liner.task_pid)
                    with self._lock:
                        self._running_tasks[task_id] = [future, task_name, priority]
                        self._running_task_names.add(task_name)

                    future.add_done_callback(partial(self._task_done, task_id))
                except Exception as error:
                    shared_status_info_liner.task_status_queue.put(("failed", task_id, None, None, None, error, None))
                finally:
                    with self._lock:
                        self._task_add_lock = False

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
            result = future.result()  # Get the task result, where the exception will be thrown

        except (KeyboardInterrupt, BrokenExecutor, BrokenPipeError):
            logger.warning(f"task | {task_id} | cancelled, forced termination")
            shared_status_info_liner.task_status_queue.put(("cancelled", task_id, None, None, None, None, None))
            result = "cancelled action"

        except Exception as error:
            if config["exception_thrown"]:
                raise

            logger.error(f"task | {task_id} | execution failed: {error}")
            shared_status_info_liner.task_status_queue.put(("failed", task_id, None, None, None, error, None))
            result = "failed action"

        finally:
            # Prepare result for storage (without lock)
            store_in_network = config["network_storage_results"]
            serialized_result = None
            if store_in_network:
                serialized_result = dill.dumps(result)

            # Update status and store result with minimal lock
            with self._lock:
                if result not in ["timeout action", "cancelled action", "failed action"]:
                    shared_status_info_liner.task_status_queue.put(("completed", task_id, None, None, None, None, None))
                    if result is not None:
                        if store_in_network:
                            pass  # will store outside lock
                        else:
                            self._task_results[task_id] = [result, time.time()]
                    else:
                        if store_in_network:
                            pass
                        else:
                            self._task_results[task_id] = ["completed action", time.time()]
                else:
                    if store_in_network:
                        pass
                    else:
                        self._task_results[task_id] = [result, time.time()]

                # Remove from running tasks
                if task_id in self._running_tasks:
                    task_info = self._running_tasks.pop(task_id, None)
                    self._running_task_names.discard(task_info[1])

                # Check if all tasks are completed
                if self._task_queue.empty() and len(self._running_tasks) == 0:
                    self._reset_idle_timer()

            # Perform network storage outside lock (I/O operation)
            if store_in_network:
                store_task_result(task_id, serialized_result)

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
            self._scheduler_thread.join(timeout=1.0)

    def force_stop_task(self,
                        task_id: str) -> bool:
        """
        Force stop a task by its task ID.

        Args:
            task_id: Task ID.

        Returns:
            Whether the task was successfully force stopped.
        """
        with self._lock:
            task_info = self._running_tasks.get(task_id)
            if not task_info:
                # Task might have already completed, but send kill signal anyway
                shared_status_info_liner.task_signal_transmission[task_id] = ["resume", "kill"]
                shared_status_info_liner.task_status_queue.put(
                    ("cancelled", task_id, None, None, time.time(), None, None))
                return True

            future = task_info[0]

        # Perform cancellation outside the lock to avoid deadlocks
        if not future.running():
            future.cancel()
        else:
            try:
                shared_status_info_liner.task_signal_transmission[task_id] = ["resume", "kill"]
            except Exception as error:
                logger.error(f"task | {task_id} | error sending termination signal: {error}")
                return False

        shared_status_info_liner.task_status_queue.put(("cancelled", task_id, None, None, time.time(), None, None))
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
        try:

            shared_status_info_liner.task_signal_transmission[task_id] = ["pause"]

            shared_status_info_liner.task_status_queue.put(("paused", task_id, None, None, None, None, None))
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
        try:
            shared_status_info_liner.task_signal_transmission[task_id] = ["resume"]

            shared_status_info_liner.task_status_queue.put(("running", task_id, None, None, None, None, None))
            logger.info(f"task | {task_id} | resumed")
            return True
        except Exception as error:
            logger.error(f"task | {task_id} | error during resume: {error}")
            return False

    def get_task_result(self,
                        task_id: str) -> Optional[Any]:
        """
        Get the result of a task. If there is a result, return and delete the oldest result; if no result, return None.

        Args:
            task_id: Task ID.

        Returns:
            Task return result, or None if the task is not completed or does not exist.
        """
        with self._lock:
            if task_id in self._task_results:
                result = self._task_results[task_id][0]
                del self._task_results[task_id]
                return result
        return None


cpu_liner_task = CpuLinerTask()
