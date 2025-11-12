# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""IO-bound asynchronous task execution module.

This module provides a task scheduler for IO-bound asynchronous tasks using
asyncio event loops with per-task-name isolation and thread-safe operations.
"""
import asyncio
import queue
import threading
import time
import platform

from typing import Dict, Tuple, Callable, Optional, Any, List
from concurrent.futures import Future, CancelledError
from functools import partial

from ..common import logger, config
from ..manager import task_status_manager
from ..control import ThreadTaskManager
from ..handling import ThreadSuspender
from .utils import retry_on_error_decorator_check

# Create Manager instance
_task_manager = ThreadTaskManager()
_threadsuspender = ThreadSuspender()


# A function that executes a task
async def _execute_task(task: Tuple[bool, str, str, Callable, Tuple, Dict]) -> Any:
    """
    Execute an asynchronous task.

    Args:
        task: Tuple containing task details.
            - timeout_processing: Whether timeout processing is enabled.
            - task_name: Name of the task.
            - task_id: ID of the task.
            - func: The function to execute.
            - args: Arguments to pass to the function.
            - kwargs: Keyword arguments to pass to the function.

    Returns:
        Result of the task execution or error message.
    """
    # Unpack task tuple into local variables
    timeout_processing, task_name, task_id, func, args, kwargs = task
    logger.debug(f"Start running task | {task_id} | ")
    result = None
    try:
        with _threadsuspender.suspend_context() as pause_ctx:
            _task_manager.add(None, None, pause_ctx, task_id)
            # Modify the task status
            task_status_manager.add_task_status(task_id, None, "running", time.time(), None, None, None, None)

            # If the task needs timeout processing, set the timeout time
            if timeout_processing:
                if retry_on_error_decorator_check(func):
                    result = await asyncio.wait_for(func(task_id, *args, **kwargs),
                                                    timeout=config["watch_dog_time"])
                else:
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=config["watch_dog_time"])
            else:
                if retry_on_error_decorator_check(func):
                    result = await func(task_id, *args, **kwargs)
                else:
                    result = await func(*args, **kwargs)

        _task_manager.remove(task_id)
    except asyncio.TimeoutError:
        logger.warning(f"task | {task_id} | timed out, forced termination")
        task_status_manager.add_task_status(task_id, None, "timeout", None, None, None, None, None)
        result = "timeout action"
    except asyncio.CancelledError:
        logger.warning(f"task | {task_id} | was cancelled")
        task_status_manager.add_task_status(task_id, None, "cancelled", None, None, None,
                                            None, None)
        result = "cancelled action"
    finally:
        if _task_manager.exists(task_id):
            _task_manager.remove(task_id)

    return result


class IoAsyncioTask:
    """
    Asynchronous task manager class, responsible for scheduling, executing, and monitoring asynchronous tasks.
    """
    __slots__ = [
        '_task_queues', '_running_tasks',
        '_lock', '_scheduler_lock',
        '_scheduler_started', '_scheduler_stop_event', '_scheduler_threads',
        '_event_loops',
        '_idle_timers', '_idle_timeout', '_idle_timer_lock',
        '_task_results', '_task_counters'
    ]

    def __init__(self) -> None:
        """
        Initialize the asynchronous task manager.
        """
        self._task_queues: Dict[str, queue.Queue] = {}  # Task queues for each task name
        self._running_tasks: Dict[str, List[Any]] = {}  # Running tasks

        self._lock = threading.Condition()  # Condition variable for thread synchronization
        self._scheduler_lock = threading.RLock()  # Reentrant lock for scheduler operations

        self._scheduler_started = False  # Whether the scheduler thread has started
        self._scheduler_stop_event = threading.Event()  # Scheduler thread stop event
        self._scheduler_threads: Dict[str, threading.Thread] = {}  # Scheduler threads for each task name

        self._event_loops: Dict[str, Any] = {}  # Event loops for each task name

        self._idle_timers: Dict[str, threading.Timer] = {}  # Idle timers for each task name
        self._idle_timeout = config["max_idle_time"]  # Idle timeout, default is 60 seconds
        self._idle_timer_lock = threading.Lock()  # Idle timer lock

        self._task_results: Dict[str, List[Any]] = {}  # Store task return results
        self._task_counters: Dict[str, int] = {}  # Used to track the number of tasks being executed in each event loop

    # Add the task to the scheduler
    def add_task(self,
                 timeout_processing: bool,
                 task_name: str,
                 task_id: str,
                 func: Callable,
                 *args,
                 **kwargs) -> Any:
        """
        Add a task to the task queue.

        Args:
            timeout_processing: Whether to enable timeout processing.
            task_name: Task name (can be repeated).
            task_id: Task ID (must be unique).
            func: Task function.
            *args: Positional arguments for the task function.
            **kwargs: Keyword arguments for the task function.

        Returns:
            Whether the task was successfully added.
        """
        try:
            with self._scheduler_lock:
                # Use atomic operations for queue creation and size check
                if task_name not in self._task_queues:
                    self._task_queues[task_name] = queue.Queue()

                # Atomic queue size check
                queue_size = self._task_queues[task_name].qsize()
                if queue_size >= config["io_asyncio_task"]:
                    return False

                task_status_manager.add_task_status(task_id, None, "waiting", None, None, None, None, "io_asyncio_task")

                self._task_queues[task_name].put((timeout_processing, task_name, task_id, func, args, kwargs))

                # If the scheduler thread has not started, start it
                if (task_name not in self._scheduler_threads or
                        not self._scheduler_threads[task_name].is_alive()):
                    self._event_loops[task_name] = asyncio.new_event_loop()
                    self._task_counters[task_name] = 0  # Initialize the task counter
                    self._start_scheduler(task_name)

                # Cancel the idle timer
                self._cancel_idle_timer(task_name)

                with self._lock:
                    self._lock.notify()  # Notify the scheduler thread that a new task is available

                return True
        except Exception as error:
            return error

    # Start the scheduler
    def _start_scheduler(self,
                         task_name: str) -> None:
        """
        Start the scheduler thread and the event loop thread for a specific task name.

        Args:
            task_name: Task name.
        """
        with self._lock:
            if (task_name not in self._scheduler_threads or
                    not self._scheduler_threads[task_name].is_alive()):
                self._scheduler_started = True
                self._scheduler_threads[task_name] = threading.Thread(
                    target=self._scheduler, args=(task_name,), daemon=True)
                self._scheduler_threads[task_name].start()

                # Start the event loop thread
                threading.Thread(target=self._run_event_loop, args=(task_name,), daemon=True).start()

    # Stop the scheduler
    def _stop_scheduler(self,
                        task_name: str) -> None:
        """
        Stop the scheduler and event loop for a specific task name.

        Args:
            task_name: Task name.
        """
        with self._scheduler_lock:
            # Check if all tasks are completed - use atomic operations with lock
            with self._lock:
                queue_empty = (task_name not in self._task_queues or
                               self._task_queues[task_name].empty())
                running_tasks_empty = len(self._running_tasks) == 0

                if not queue_empty or not running_tasks_empty:
                    logger.debug(f"task was detected to be running, and the task stopped terminating")
                    return None

            self._scheduler_stop_event.set()

            with self._lock:
                self._scheduler_started = False
                self._lock.notify_all()

            # Clear the task queue
            self._clear_task_queue(task_name)

            # Stop the event loop
            self._stop_event_loop(task_name)

            # Wait for the scheduler thread to finish
            self._join_scheduler_thread(task_name)

            # Reset parameters for scheduler restart - use atomic operations
            with self._lock:
                if task_name in self._event_loops:
                    del self._event_loops[task_name]
                if task_name in self._scheduler_threads:
                    del self._scheduler_threads[task_name]
                if task_name in self._task_queues:
                    del self._task_queues[task_name]
                if task_name in self._idle_timers:
                    del self._idle_timers[task_name]
                if task_name in self._task_counters:
                    del self._task_counters[task_name]

            logger.debug(
                f"Scheduler event loop | {task_name} | have stopped")
        return None

    def stop_all_schedulers(self,
                            system_operations: bool = False) -> None:
        """
        Stop all schedulers and event loops, and forcibly kill all tasks if force_cleanup is True.

        Args:
            system_operations: System execution metrics.
        """
        # Turn off the scheduler
        self._scheduler_stop_event.set()

        # Notify all waiting threads first
        with self._lock:
            self._lock.notify_all()

        with self._scheduler_lock:
            # Check if all tasks are completed - use atomic operations
            if system_operations:
                with self._lock:
                    queues_empty = all(q.empty() for q in self._task_queues.values())
                    running_tasks_empty = len(self._running_tasks) == 0

                    if not queues_empty or not running_tasks_empty:
                        logger.debug(f"task was detected to be running, and the task stopped terminating")
                        return None

            # Forcibly cancel all running tasks
            _task_manager.cancel_all_tasks()

            with self._lock:
                self._scheduler_started = False
                self._lock.notify_all()

            # Clear all task queues
            for task_name in list(self._task_queues.keys()):
                self._clear_task_queue(task_name)

            # Stop all event loops
            for task_name in list(self._event_loops.keys()):
                self._stop_event_loop(task_name)

            # Wait for all scheduler threads to finish
            for task_name in list(self._scheduler_threads.keys()):
                self._join_scheduler_thread(task_name)

            self._wait_tasks_end()
            # Reset all parameters - use atomic operations with lock
            with self._lock:
                self._task_results.clear()
                self._event_loops.clear()
                self._scheduler_threads.clear()
                self._task_queues.clear()
                self._idle_timers.clear()
                self._task_counters.clear()
                self._running_tasks.clear()

            # Reset stop event for potential reuse
            self._scheduler_stop_event.clear()

            logger.debug(
                "Scheduler and event loop have stopped, all resources have been released and parameters reset")
        return None

    def _wait_tasks_end(self) -> None:
        """
        Wait for all tasks to finish
        """
        while True:
            if len(self._running_tasks) == 0:
                break
            time.sleep(0.01)

    # Task scheduler
    def _scheduler(self,
                   task_name: str) -> None:
        """
        Scheduler function, fetch tasks from the task queue and submit them to the event loop for execution.

        Args:
            task_name: Task name.
        """
        asyncio.set_event_loop(self._event_loops[task_name])

        while not self._scheduler_stop_event.is_set():
            with self._lock:
                # Use loop and timeout to prevent spurious wakeup
                while ((task_name not in self._task_queues or
                        self._task_queues[task_name].empty() or
                        self._task_counters[task_name] >= config["io_asyncio_task"]) and
                       not self._scheduler_stop_event.is_set()):
                    self._lock.wait(timeout=1.0)  # Add timeout to prevent permanent waiting

                if self._scheduler_stop_event.is_set():
                    break

                # Check conditions again due to possible spurious wakeup
                if (task_name not in self._task_queues or
                        self._task_queues[task_name].empty()):
                    continue

                task = self._task_queues[task_name].get()

            # Execute the task after the lock is released
            timeout_processing, task_name, task_id, func, args, kwargs = task
            future = asyncio.run_coroutine_threadsafe(_execute_task(task), self._event_loops[task_name])
            _task_manager.add(future, None, None, task_id)

            # Use lock protection for shared state updates
            with self._lock:
                self._running_tasks[task_id] = [future, task_name]
                self._task_counters[task_name] += 1

            future.add_done_callback(partial(self._task_done, task_id, task_name))

    def _task_done(self,
                   task_id: str,
                   task_name: str,
                   future: Future) -> None:
        """
        Callback function after a task is completed.

        Args:
            task_id: Task ID.
            task_name: Task name.
            future: Future object corresponding to the task.
        """
        try:
            result = future.result()
        except CancelledError:
            result = "cancelled action"
        except Exception as error:
            if config["exception_thrown"]:
                raise

            logger.error(f"task | {task_id} | execution failed: {error}")
            task_status_manager.add_task_status(task_id, None, "failed", None, None, error, None, None)
            result = "failed action"

        # Save the result returned by the task - use lock protection
        with self._lock:
            if result not in ["timeout action", "cancelled action", "failed action"]:
                if result is not None:
                    self._task_results[task_id] = [result, time.time()]
                else:
                    self._task_results[task_id] = ["completed action", time.time()]
            else:
                self._task_results[task_id] = [result, time.time()]

            # Remove the task from running tasks dictionary
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]

            # Decrement task counters (ensure it doesn't go below 0)
            if task_name in self._task_counters and self._task_counters[task_name] > 0:
                self._task_counters[task_name] -= 1

            # Update task status
            if result not in ["timeout action", "cancelled action", "failed action"]:
                task_status_manager.add_task_status(task_id, None, "completed", None, time.time(), None, None, None)

            # Check if all tasks are completed
            if (task_name in self._task_queues and
                    self._task_queues[task_name].empty() and
                    len(self._running_tasks) == 0):
                self._reset_idle_timer(task_name)

            # Notify the scheduler to continue scheduling new tasks
            self._lock.notify()

    # The task scheduler closes the countdown
    def _reset_idle_timer(self,
                          task_name: str) -> None:
        """
        Reset the idle timer for a specific task name.

        Args:
            task_name: Task name.
        """
        with self._idle_timer_lock:
            if task_name in self._idle_timers and self._idle_timers[task_name] is not None:
                self._idle_timers[task_name].cancel()
            self._idle_timers[task_name] = threading.Timer(self._idle_timeout, self._idle_timeout_callback,
                                                           args=(task_name,))
            self._idle_timers[task_name].daemon = True
            self._idle_timers[task_name].start()

    def _idle_timeout_callback(self, task_name: str) -> None:
        """
        Callback for idle timeout.

        Args:
            task_name: Task name.
        """
        self._stop_scheduler(task_name)

    def _cancel_idle_timer(self,
                           task_name: str) -> None:
        """
        Cancel the idle timer for a specific task name.

        Args:
            task_name: Task name.
        """
        with self._idle_timer_lock:
            if task_name in self._idle_timers and self._idle_timers[task_name] is not None:
                self._idle_timers[task_name].cancel()
                del self._idle_timers[task_name]

    def _clear_task_queue(self,
                          task_name: str) -> None:
        """
        Clear the task queue for a specific task name.

        Args:
            task_name: Task name.
        """
        if task_name in self._task_queues:
            try:
                while True:
                    self._task_queues[task_name].get_nowait()
            except queue.Empty:
                pass

    def _join_scheduler_thread(self,
                               task_name: str) -> None:
        """
        Wait for the scheduler thread to finish for a specific task name.

        Args:
            task_name: Task name.
        """
        if task_name in self._scheduler_threads and self._scheduler_threads[task_name].is_alive():
            self._scheduler_threads[task_name].join(timeout=5.0)  # Add timeout to prevent permanent waiting

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
                logger.debug(f"task | {task_id} | does not exist or is already completed")
                return False

            future = task_info[0]

        # Perform cancellation outside the lock to avoid deadlocks
        try:
            if not future.running():
                future.cancel()
            else:
                # First ensure that the task is not paused.
                if platform.system() == "Windows":
                    _task_manager.resume_task(task_id)
                _task_manager.cancel_task(task_id)

            task_status_manager.add_task_status(task_id, None, "cancelled", None, time.time(), None, None,
                                                "io_asyncio_task")
            return True
        except Exception as e:
            logger.error(f"task | {task_id} | error during force stop: {e}")
            return False

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
            if task_id not in self._running_tasks:
                logger.warning(f"task | {task_id} | does not exist or is already completed")
                return False

        if not platform.system() == "Windows":
            logger.warning(f"Pause and resume functionality is not supported on Linux and Mac!")
            return False

        try:
            _task_manager.pause_task(task_id)
            task_status_manager.add_task_status(task_id, None, "paused", None, None, None, None, "io_asyncio_task")
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
            if task_id not in self._running_tasks:
                logger.warning(f"task | {task_id} | does not exist or is already completed")
                return False

        if not platform.system() == "Windows":
            logger.warning(f"Pause and resume functionality is not supported on Linux and Mac!")
            return False

        try:
            _task_manager.resume_task(task_id)
            task_status_manager.add_task_status(task_id, None, "running", None, None, None, None, "io_asyncio_task")
            logger.info(f"task | {task_id} | resumed")
            return True
        except Exception as e:
            logger.error(f"task | {task_id} | error during resume: {e}")
            return False

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
        # Use lock protection for results dictionary access and modification
        with self._lock:
            if task_id in self._task_results:
                result = self._task_results[task_id][0]
                del self._task_results[task_id]  # Delete the results
                return result
        return None

    def _run_event_loop(self,
                        task_name: str) -> None:
        """
        Run the event loop for a specific task name.

        Args:
            task_name: Task name.
        """
        asyncio.set_event_loop(self._event_loops[task_name])
        self._event_loops[task_name].run_forever()

    def _stop_event_loop(self, task_name: str) -> None:
        """
        Stop the event loop for a specific task name.

        Args:
            task_name: Task name.
        """
        if (task_name in self._event_loops and
                self._event_loops[task_name].is_running()):
            try:
                # First cancel all unfinished tasks
                loop = self._event_loops[task_name]

                # Perform cleanup in the event loop thread
                future = asyncio.run_coroutine_threadsafe(
                    self._cleanup_tasks(task_name),
                    loop
                )

                try:
                    future.result(timeout=5.0)  # Wait up to 5 seconds
                except Exception:
                    logger.warning(f"Cleanup timeout for task {task_name}")

                # Then stop the event loop
                loop.call_soon_threadsafe(loop.stop)

            except Exception as error:
                logger.debug(f"task | stopping event loop | error occurred: {error}")

    async def _cleanup_tasks(self, task_name: str):
        """Clear unfinished tasks"""
        loop = self._event_loops[task_name]
        tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]

        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


io_asyncio_task = IoAsyncioTask()
