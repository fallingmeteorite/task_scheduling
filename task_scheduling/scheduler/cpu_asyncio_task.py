# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""CPU-bound asynchronous task execution module.

This module provides a task scheduler for CPU-bound asynchronous tasks using
process pool execution with asyncio event loops in separate processes.
"""
import asyncio
import queue
import os
import threading
import time
import dill

from concurrent.futures import ProcessPoolExecutor, Future, BrokenExecutor
from functools import partial
from typing import Callable, Dict, Tuple, Optional, Any, List
from task_scheduling.common import logger, config
from task_scheduling.manager import task_status_manager
from task_scheduling.control import ProcessTaskManager
from task_scheduling.handling import ThreadTerminator, StopException, ThreadSuspender
from task_scheduling.result_server import store_task_result
from task_scheduling.scheduler.utils import exit_cleanup, SharedStatusInfo, retry_on_error_decorator_check, \
    DillProcessPoolExecutor

shared_status_info_asyncio = SharedStatusInfo()


async def _execute_task_async(task: Tuple[bool, str, str, Callable, Tuple, Dict],
                              task_status_queue: queue.Queue, task_manager: Any) -> Any:
    """
    Execute a task asynchronously and handle its status.

    Args:
        task: A tuple containing task details.
            - timeout_processing: Whether timeout processing is enabled.
            - task_name: Name of the task.
            - task_id: ID of the task.
            - func: The function to execute.
            - args: Arguments to pass to the function.
            - kwargs: Keyword arguments to pass to the function.
        task_status_queue: Queue to update task status.

    Returns:
        Result of the task execution or error message.
    """
    timeout_processing, task_name, task_id, func, args, kwargs = task
    logger.debug(f"Start running task, task ID: {task_id}")

    with ThreadTerminator().terminate_control() as terminate_ctx:
        with ThreadSuspender() as pause_ctx:
            task_manager.add(terminate_ctx, pause_ctx, task_id)

            task_status_queue.put(("running", task_id, None, time.time(), None, None, None))

            if timeout_processing:
                if retry_on_error_decorator_check(func):
                    result = await asyncio.wait_for(func(task_id, *args, **kwargs),
                                                    timeout=config["watch_dog_time"])
                else:
                    result = await asyncio.wait_for(func(*args, **kwargs),
                                                    timeout=config["watch_dog_time"])
            else:
                if retry_on_error_decorator_check(func):
                    result = await func(task_id, *args, **kwargs)
                else:
                    result = await func(*args, **kwargs)

    return result


def _execute_task(task: Tuple[bool, str, str, Callable, Tuple, Dict],
                  task_status_queue: queue.Queue,
                  task_signal_transmission: dict,
                  task_pid: dict) -> Any:
    """
    Execute a task using an asyncio event loop.

    Args:
        task: A tuple containing task details.
            - timeout_processing: Whether timeout processing is enabled.
            - task_name: Name of the task.
            - task_id: ID of the task.
            - func: The function to execute.
            - args: Arguments to pass to the function.
            - kwargs: Keyword arguments to pass to the function.
        task_status_queue: Queue to update task status.
        task_signal_transmission: Dict to transmission signal.
        task_pid: Dict to process task pid.

    Returns:
        Result of the task execution or error message.
    """
    _, _, task_id, _, _, _ = task
    task_pid[task_id] = os.getpid()
    task_manager = ProcessTaskManager(task_signal_transmission)
    try:
        result = asyncio.run(_execute_task_async(task, task_status_queue, task_manager))
    except StopException:
        logger.warning(f"task | {task_id} | cancelled, forced termination")
        task_status_queue.put(("cancelled", task_id, None, None, None, None, None))
        result = "cancelled action"

    except asyncio.TimeoutError:
        logger.warning(f"task | {task_id} | timed out, forced termination")
        task_status_queue.put(("timeout", task_id, None, None, None, None, None))
        result = "timeout action"

    except Exception as error:
        if config["exception_thrown"]:
            raise

        # if not "Cannot close a running event loop" in str(e):
        logger.error(f"task | {task_id} | execution failed: {error}")
        task_status_queue.put(("failed", task_id, None, None, None, error, None))
        result = "failed action"

    finally:
        # Remove main thread logging
        if task_manager.exists(task_id):
            task_manager.remove(task_id)

        # Clean up PID mapping
        if task_id in task_pid:
            del task_pid[task_id]
    return result


class CpuAsyncioTask:
    """
    Linear task manager class, responsible for managing the scheduling, execution, and monitoring of linear tasks.
    """
    __slots__ = [
        '_task_queue', '_running_tasks', '_running_task_names',
        '_lock', '_condition', '_scheduler_lock',
        '_scheduler_started', '_scheduler_stop_event', '_scheduler_thread',
        '_idle_timer', '_idle_timeout', '_idle_timer_lock',
        '_task_results',
        '_executor', '_status_thread'
    ]

    def __init__(self) -> None:
        """
        Initialize the CpuAsyncTask manager.
        """
        self._task_queue = queue.Queue()  # Task queue
        self._running_tasks = {}  # Running tasks
        self._running_task_names = set()  # Running task names for O(1) duplicate checks

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
        while not self._scheduler_stop_event.is_set() or not shared_status_info_asyncio.task_status_queue.empty():
            try:
                task = shared_status_info_asyncio.task_status_queue.get(timeout=0.1)
                status, task_id, task_name, start_time, end_time, error, timeout_processing = task
                task_status_manager.add_task_status(task_id, task_name, status, start_time, end_time, error,
                                                    timeout_processing, "cpu_asyncio_task")
            except (queue.Empty, ValueError, EOFError, BrokenPipeError):
                pass  # Ignore empty queue exceptions

    def add_task(self,
                 timeout_processing: bool,
                 task_name: str,
                 task_id: str,
                 func: Callable,
                 *args,
                 **kwargs) -> Any:
        """
        Add the task to the scheduler.

        Args:
            timeout_processing: Whether timeout processing is enabled.
            task_name: Task name.
            task_id: Task ID.
            func: The function to execute.
            *args: Arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            Whether the task was successfully added.
        """
        try:
            # 1. Capacity check (lock only for shared state)
            with self._lock:
                queue_size = self._task_queue.qsize()
                if queue_size >= config["cpu_asyncio_task"] or len(self._running_tasks) >= config["cpu_asyncio_task"]:
                    return False
                if task_name in self._running_task_names:
                    return False

            # 2. Status updates (queue is thread-safe)
            shared_status_info_asyncio.task_status_queue.put(("queuing", task_id, None, None, None, None, None))
            shared_status_info_asyncio.task_status_queue.put(("waiting", task_id, None, None, None, None, None))

            # 3. Put task into queue (thread-safe)
            self._task_queue.put((timeout_processing, task_name, task_id, func, args, kwargs))

            # 4. Start scheduler if needed (only protect start flag)
            with self._scheduler_lock:
                if self._scheduler_stop_event.is_set() and not self._scheduler_started:
                    self._join_scheduler_thread()
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
                        return

            # Resume all paused tasks (lock only for accessing _running_tasks)
            with self._lock:
                for task_id, _ in self._running_tasks.items():
                    shared_status_info_asyncio.task_signal_transmission[task_id] = ["resume", "kill"]

            # Shutdown executor (no lock needed)
            if self._executor:
                self._executor.shutdown(wait=False, cancel_futures=True)

            # Clear the task queue
            self._clear_task_queue()

            # Wait for scheduler thread to finish (no lock needed)
            self._join_scheduler_thread()

            # Wait for status thread to finish
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

            self._scheduler_thread = None

            # Cancel idle timer (has its own lock)
            with self._idle_timer_lock:
                if self._idle_timer is not None:
                    self._idle_timer.cancel()
                    self._idle_timer = None

            logger.debug(
                "Scheduler and event loop have stopped, all resources have been released and parameters reset")

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
        with DillProcessPoolExecutor(max_workers=int(config["cpu_asyncio_task"]),
                                     initializer=exit_cleanup) as executor:
            self._executor = executor
            while not self._scheduler_stop_event.is_set():
                task = None
                # Wait for task with condition, but release lock before submitting
                with self._condition:
                    while (self._task_queue.empty() and
                           not self._scheduler_stop_event.is_set()):
                        self._condition.wait()

                    if self._scheduler_stop_event.is_set():
                        break

                    try:
                        task = self._task_queue.get_nowait()
                    except queue.Empty:
                        continue

                if task is None:
                    continue

                timeout_processing, task_name, task_id, func, args, kwargs = task

                # Submit to executor (no lock held)
                try:
                    future = executor.submit(_execute_task, task, shared_status_info_asyncio.task_status_queue,
                                             shared_status_info_asyncio.task_signal_transmission,
                                             shared_status_info_asyncio.task_pid)
                    with self._lock:
                        self._running_tasks[task_id] = [future, task_name]
                        self._running_task_names.add(task_name)

                    future.add_done_callback(partial(self._task_done, task_id))
                except Exception as error:
                    shared_status_info_asyncio.task_status_queue.put(("failed", task_id, None, None, None, error, None))

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
            shared_status_info_asyncio.task_status_queue.put(("cancelled", task_id, None, None, None, None, None))
            result = "cancelled action"

        except Exception as error:
            if config["exception_thrown"]:
                raise

            logger.error(f"task | {task_id} | execution failed: {error}")
            shared_status_info_asyncio.task_status_queue.put(("failed", task_id, None, None, None, error, None))
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
                    shared_status_info_asyncio.task_status_queue.put(
                        ("completed", task_id, None, None, None, None, None))
                    if result is not None:
                        if not network_storage:
                            self._task_results[task_id] = [result, time.time()]
                    else:
                        if not network_storage:
                            self._task_results[task_id] = ["completed action", time.time()]
                else:
                    if not network_storage:
                        self._task_results[task_id] = [result, time.time()]

                # Remove from running tasks
                task_info = self._running_tasks.pop(task_id, None)
                if task_info is not None:
                    self._running_task_names.discard(task_info[1])

                # Check if all tasks are completed
                if self._task_queue.empty() and len(self._running_tasks) == 0:
                    self._reset_idle_timer()

            # Perform network storage outside lock (I/O operation)
            if network_storage:
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
        with self._lock:
            task_info = self._running_tasks.get(task_id)
            if not task_info:
                logger.warning(f"task | {task_id} | does not exist or is already completed")
                return False
            future = task_info[0]

            # Try to cancel the future if not running
            if not future.running():
                future.cancel()
                return True

        # Send termination signal to running task (outside lock)
        shared_status_info_asyncio.task_signal_transmission[task_id] = ["resume", "kill"]

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
        with self._lock:
            if task_id not in self._running_tasks:
                logger.warning(f"task | {task_id} | does not exist or is already completed")
                return False

        shared_status_info_asyncio.task_signal_transmission[task_id] = ["pause"]

        shared_status_info_asyncio.task_status_queue.put(("paused", task_id, None, None, None, None, None))
        logger.info(f"task | {task_id} | paused")
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
        with self._lock:
            if task_id not in self._running_tasks:
                logger.warning(f"task | {task_id} | does not exist or is already completed")
                return False

        shared_status_info_asyncio.task_signal_transmission[task_id] = ["resume"]

        shared_status_info_asyncio.task_status_queue.put(("running", task_id, None, None, None, None, None))
        logger.info(f"task | {task_id} | resumed")
        return True

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


cpu_asyncio_task = CpuAsyncioTask()
