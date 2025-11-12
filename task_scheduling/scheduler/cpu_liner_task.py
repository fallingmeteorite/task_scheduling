# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""CPU-bound linear task execution module.

This module provides a task scheduler for CPU-bound linear tasks using
process pool execution with priority-based scheduling and timeout handling.
"""
import math
import queue
import os
import threading
import time
import platform
import signal
import multiprocessing

from concurrent.futures import ProcessPoolExecutor, Future, BrokenExecutor
from functools import partial
from multiprocessing.managers import DictProxy
from typing import Callable, Dict, Tuple, Optional, Any, List

from ..common import logger, config
from ..control import ProcessTaskManager
from ..handling import ThreadTerminator, StopException, ThreadSuspender, TimeoutException, ThreadingTimeout
from ..manager import task_status_manager, SharedTaskDict
from .utils import exit_cleanup, TaskCounter, SharedStatusInfo, get_param_count, retry_on_error_decorator_check

_task_counter = TaskCounter("cpu_liner_task")
_threadsuspender = ThreadSuspender()
_threadterminator = ThreadTerminator()
shared_status_info_liner = SharedStatusInfo()


def _execute_task(task: Tuple[bool, str, str, Callable, str, Tuple, Dict],
                  task_status_queue: queue.Queue,
                  task_signal_transmission: DictProxy,
                  task_pid: DictProxy) -> Any:
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
        with _threadterminator.terminate_control() as terminate_ctx:
            with _threadsuspender.suspend_context() as pause_ctx:
                task_manager.add(terminate_ctx, pause_ctx, task_id)

                task_status_queue.put(("running", task_id, None, time.time(), None, None, None))

                if timeout_processing:
                    with ThreadingTimeout(seconds=config["watch_dog_time"], swallow_exc=False):
                        # Whether to pass in the task manager to facilitate other thread management
                        # Check whether the function needs to use hyperthreading
                        if get_param_count(func, *args, **kwargs):
                            share_info = (task_name, task_manager, _threadterminator, StopException, ThreadingTimeout,
                                          TimeoutException, _threadsuspender, task_status_queue)
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
                        share_info = (task_name, task_manager, _threadterminator, StopException, ThreadingTimeout,
                                      TimeoutException, _threadsuspender, task_status_queue)
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
        '_task_queue', '_running_tasks',
        '_lock', '_condition', '_scheduler_lock',
        '_scheduler_started', '_scheduler_stop_event', '_scheduler_thread',
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

        self._executor: Optional[ProcessPoolExecutor] = None

        # Start a thread to handle task status updates
        self._status_thread = threading.Thread(target=self._handle_task_status_updates, daemon=True)

    def _handle_task_status_updates(self) -> None:
        """
        Handle task status updates from the task status queue.
        """
        while not self._scheduler_stop_event.is_set() or not shared_status_info_liner.task_status_queue.empty():
            try:
                task = shared_status_info_liner.task_status_queue.get(timeout=0.01)
                status, task_id, task_name, start_time, end_time, error, timeout_processing = task
                task_status_manager.add_task_status(task_id, task_name, status, start_time, end_time, error,
                                                    timeout_processing, "cpu_liner_task")

            except (queue.Empty, ValueError):
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
            with self._scheduler_lock:
                shared_status_info_liner.task_status_queue.put(("queuing", task_id, None, None, None, None, None))

                # Use atomic operations for queue size check and running tasks check
                with self._lock:
                    if not _task_counter.is_high_priority(priority):
                        queue_size = self._task_queue.qsize()
                        running_task_names = {details[1] for details in self._running_tasks.values()}

                        if queue_size >= config["cpu_liner_task"]:
                            return False

                        if task_name in running_task_names:
                            return False
                    else:
                        if not _task_counter.add_count(math.ceil(config["cpu_liner_task"])):
                            return False

                if self._scheduler_stop_event.is_set() and not self._scheduler_started:
                    self._join_scheduler_thread()

                # Reduce the granularity of the lock
                shared_status_info_liner.task_status_queue.put(("waiting", task_id, None, None, None, None, None))

                self._task_queue.put((timeout_processing, task_name, task_id, func, priority, args, kwargs))

                if not self._scheduler_started:
                    self._start_scheduler()

                with self._condition:
                    self._condition.notify()

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
        # Turn off the scheduler
        self._scheduler_stop_event.set()

        # Notify all waiting threads first
        with self._condition:
            self._condition.notify_all()

        with self._scheduler_lock:
            # Check if there are any running tasks - use atomic operations
            if system_operations:
                with self._lock:
                    queue_empty = self._task_queue.empty()
                    running_tasks_empty = len(self._running_tasks) == 0

                    if not queue_empty or not running_tasks_empty:
                        logger.warning(f"Cpu liner task | detected running tasks | stopping operation terminated")
                        return None

            # First cancel the task pause - use atomic operations
            with self._lock:
                for task_id, _ in self._running_tasks.items():
                    if platform.system() in ("Linux", "Darwin"):
                        os.kill(shared_status_info_liner.task_pid.get(task_id), signal.SIGCONT)
                    shared_status_info_liner.task_signal_transmission[task_id] = ["resume", "kill"]

            # Ensure the executor is properly shut down
            if self._executor:
                # Use wait=True for safe shutdown in No GIL environment
                self._executor.shutdown(wait=False, cancel_futures=True)

            # Clear the task queue
            self._clear_task_queue()

            # Wait for the scheduler thread to finish
            self._join_scheduler_thread()

            # Wait for status thread to finish
            if self._status_thread.is_alive():
                self._status_thread.join(timeout=5.0)

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
            if shared_status_info_liner.task_status_queue.empty():
                break
            time.sleep(0.01)

    def _scheduler(self) -> None:
        """
        Scheduler function, fetch tasks from the task queue and submit them to the process pool for execution.
        """
        with ProcessPoolExecutor(max_workers=int(config["cpu_liner_task"] + math.ceil(config["cpu_liner_task"] / 2)),
                                 initializer=exit_cleanup, mp_context=multiprocessing.get_context('spawn')) as executor:
            self._executor = executor
            while not self._scheduler_stop_event.is_set():
                with self._condition:
                    # Use loop and timeout to prevent spurious wakeup
                    while (self._task_queue.empty() and
                           not self._scheduler_stop_event.is_set()):
                        self._condition.wait(timeout=1.0)  # Add timeout to prevent permanent waiting

                    if self._scheduler_stop_event.is_set():
                        break

                    # Check queue state again due to possible spurious wakeup
                    if self._task_queue.empty():
                        continue

                    task = self._task_queue.get()

                timeout_processing, task_name, task_id, func, priority, args, kwargs = task

                # Use lock protection for shared state updates
                try:
                    future = executor.submit(_execute_task, task, shared_status_info_liner.task_status_queue,
                                             shared_status_info_liner.task_signal_transmission,
                                             shared_status_info_liner.task_pid)
                except Exception:
                    pass

                with self._lock:
                    self._running_tasks[task_id] = [future, task_name, priority]

                future.add_done_callback(partial(self._task_done, task_id))

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
        try:
            result = future.result()  # Get the task result, where the exception will be thrown

        except (KeyboardInterrupt, BrokenExecutor, BrokenPipeError):
            # Prevent problems caused by exit errors
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
            # The storage task returns a result - use lock protection
            with self._lock:
                if result not in ["timeout action", "cancelled action", "failed action"]:
                    shared_status_info_liner.task_status_queue.put(("completed", task_id, None, None, None, None, None))
                    if result is not None:
                        self._task_results[task_id] = [result, time.time()]
                    else:
                        self._task_results[task_id] = ["completed action", time.time()]
                else:
                    self._task_results[task_id] = [result, time.time()]

                # Make sure the Future object is deleted
                if task_id in self._running_tasks:
                    del self._running_tasks[task_id]

                # Check if all tasks are completed
                if self._task_queue.empty() and len(self._running_tasks) == 0:
                    self._reset_idle_timer()

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
                if platform.system() == "Windows":
                    # First ensure that the task is not paused.
                    shared_status_info_liner.task_signal_transmission[task_id] = ["resume", "kill"]
                elif platform.system() in ("Linux", "Darwin"):
                    pid = shared_status_info_liner.task_pid.get(task_id)
                    if pid:
                        os.kill(pid, signal.SIGCONT)
                        shared_status_info_liner.task_signal_transmission[task_id] = ["kill"]
                    else:
                        logger.warning(f"task | {task_id} | no PID found for task")
            except Exception as e:
                logger.error(f"task | {task_id} | error sending termination signal: {e}")
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
        # Use lock protection for running tasks dictionary access
        with self._lock:
            if task_id not in self._running_tasks and not platform.system() == "Windows":
                logger.warning(f"The pause signal must be issued in the main thread.")
                return False

        try:
            if platform.system() == "Windows":
                # Use lock protection for running tasks dictionary access
                shared_status_info_liner.task_signal_transmission[task_id] = ["pause"]
            elif platform.system() in ("Linux", "Darwin"):
                pid = shared_status_info_liner.task_pid.get(task_id)
                if pid:
                    os.kill(pid, signal.SIGSTOP)
                else:
                    logger.warning(f"task | {task_id} | no PID found for task")
                    return False

            shared_status_info_liner.task_status_queue.put(("paused", task_id, None, None, None, None, None))
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
            if task_id not in self._running_tasks and not platform.system() == "Windows":
                logger.warning(f"The resume signal must be issued in the main thread.")
                return False

        try:
            if platform.system() == "Windows":
                shared_status_info_liner.task_signal_transmission[task_id] = ["resume"]
            elif platform.system() in ("Linux", "Darwin"):
                pid = shared_status_info_liner.task_pid.get(task_id)
                if pid:
                    os.kill(pid, signal.SIGCONT)
                else:
                    logger.warning(f"task | {task_id} | no PID found for task")
                    return False

            shared_status_info_liner.task_status_queue.put(("running", task_id, None, None, None, None, None))
            logger.info(f"task | {task_id} | resumed")
            return True
        except Exception as e:
            logger.error(f"task | {task_id} | error during resume: {e}")
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
        # Use lock protection for results dictionary access and modification
        with self._lock:
            if task_id in self._task_results:
                result = self._task_results[task_id][0]
                del self._task_results[task_id]
                return result
        return None


cpu_liner_task = CpuLinerTask()
