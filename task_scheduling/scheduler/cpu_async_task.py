# -*- coding: utf-8 -*-
import asyncio
import multiprocessing
import queue
import time
from typing import Dict, List, Tuple, Callable, Optional, Any

from task_scheduling.manager.task_details_queue import task_status_manager
from ..common import logger
from ..config import config
from ..stopit import ThreadingTimeout, TimeoutException


class CpuAsyncTask:
    """
    Asynchronous task manager class, responsible for scheduling, executing, and monitoring asynchronous tasks.
    """
    __slots__ = [
        'task_queues', 'scheduler_lock', 'scheduler_started', 'scheduler_stop_event',
        'running_tasks', 'scheduler_processes', 'event_loops', 'idle_timers',
        'idle_timeout', 'idle_timer_lock', 'task_results', 'task_counters'
    ]

    def __init__(self) -> None:
        """
        Initialize the asynchronous task manager.
        """
        self.task_queues: Dict[str, multiprocessing.Queue] = {}  # Task queues for each task name
        self.scheduler_lock = multiprocessing.Lock()  # Process lock
        self.scheduler_started = False  # Whether the scheduler process has started
        self.scheduler_stop_event = multiprocessing.Event()  # Scheduler process stop event
        self.running_tasks: Dict[str, list[Any]] = {}  # Use weak references to reduce memory usage
        self.scheduler_processes: Dict[str, multiprocessing.Process] = {}  # Scheduler processes for each task name
        self.event_loops: Dict[str, Any] = {}  # Event loops for each task name
        self.idle_timers: Dict[str, multiprocessing.Process] = {}  # Idle timers for each task name
        self.idle_timeout = config["max_idle_time"]  # Idle timeout, default is 60 seconds
        self.idle_timer_lock = multiprocessing.Lock()  # Idle timer lock
        self.task_results: Dict[str, List[Any]] = {}  # Store task return results, keep up to 2 results for each task ID
        self.task_counters: Dict[str, int] = {}  # Used to track the number of tasks being executed in each event loop

    # Add the task to the scheduler
    def add_task(self, timeout_processing: bool, task_name: str, task_id: str, func: Callable, *args, **kwargs) -> bool:
        """
        Add a task to the task queue.

        :param timeout_processing: Whether to enable timeout processing.
        :param task_name: Task name (can be repeated).
        :param task_id: Task ID (must be unique).
        :param func: Task function.
        :param args: Positional arguments for the task function.
        :param kwargs: Keyword arguments for the task function.
        """
        try:
            with self.scheduler_lock:
                if task_name not in self.task_queues:
                    self.task_queues[task_name] = multiprocessing.Queue()

                if self.task_queues[task_name].qsize() >= config["maximum_queue_async"]:
                    logger.warning(f"Cpu asyncio taskCpu asyncio task | {task_id} | not added, queue is full")
                    logger.warning(f"Asyncio queue is full!!!")
                    return False

                task_status_manager.add_task_status(task_id, task_name, "pending", None, None, None,
                                                    timeout_processing)

                self.task_queues[task_name].put((timeout_processing, task_name, task_id, func, args, kwargs))

                # If the scheduler process has not started, start it
                if task_name not in self.scheduler_processes or not self.scheduler_processes[task_name].is_alive():
                    self.task_counters[task_name] = 0  # Initialize the task counter
                    self._start_scheduler(task_name)

                # Cancel the idle timer
                self._cancel_idle_timer(task_name)

                return True
        except Exception as e:
            logger.error(f"Error adding task | {task_id} |: {e}")
            return False

    # Start the scheduler
    def _start_scheduler(self, task_name: str) -> None:
        """
        Start the scheduler process and the event loop process for a specific task name.

        :param task_name: Task name.
        """
        with self.scheduler_lock:
            if task_name not in self.scheduler_processes or not self.scheduler_processes[task_name].is_alive():
                self.scheduler_started = True
                self.scheduler_processes[task_name] = multiprocessing.Process(target=self._scheduler, args=(task_name,))
                self.scheduler_processes[task_name].start()

    # Stop the scheduler
    def _stop_scheduler(self, task_name: str, force_cleanup: bool, system_operations: bool = False) -> None:
        """
        :param task_name: Task name.
        :param force_cleanup: Force the end of a running task
        Stop the scheduler and event loop, and forcibly kill all tasks if force_cleanup is True.
        :param system_operations: System execution metrics
        """
        with self.scheduler_lock:
            # Check if all tasks are completed
            if not self.task_queues[task_name].empty() or not len(self.running_tasks) == 0:
                if system_operations:
                    logger.warning(f"Cpu asyncio task | detected running tasks | stopping operation terminated")
                    return None

            logger.warning("Exit cleanup")

            self.scheduler_started = False
            self.scheduler_stop_event.set()

            if force_cleanup:
                # Forcibly cancel all running tasks
                self._cancel_all_running_tasks(task_name)
                self.scheduler_stop_event.set()
            else:
                self.scheduler_stop_event.set()

            # Clear the task queue
            self._clear_task_queue(task_name)

            # Stop the event loop
            self._stop_event_loop(task_name)

            # Wait for the scheduler process to finish
            self._join_scheduler_process(task_name)

            # Clean up all task return results
            self.task_results.clear()

            # Reset parameters for scheduler restart
            if task_name in self.event_loops:
                del self.event_loops[task_name]
            if task_name in self.scheduler_processes:
                del self.scheduler_processes[task_name]
            if task_name in self.task_queues:
                del self.task_queues[task_name]

            logger.info(
                f"Scheduler and event loop for task {task_name} have stopped, all resources have been released and parameters reset")

    def stop_all_schedulers(self, force_cleanup: bool, system_operations: bool = False) -> None:
        """
        Stop all schedulers and event loops, and forcibly kill all tasks if force_cleanup is True.

        :param force_cleanup: Force the end of all running tasks.
        :param system_operations: System execution metrics.
        """
        with self.scheduler_lock:
            # Check if all tasks are completed
            if not all(q.empty() for q in self.task_queues.values()) or len(self.running_tasks) != 0:
                if system_operations:
                    logger.warning(f"Cpu asyncio task | detected running tasks | stopping operation terminated")
                    return None

            logger.warning("Exit cleanup")

            self.scheduler_started = False
            self.scheduler_stop_event.set()

            if force_cleanup:
                # Forcibly cancel all running tasks
                for task_name in list(self.running_tasks.keys()):  # Create a copy using list()
                    self._cancel_all_running_tasks(task_name)
                self.scheduler_stop_event.set()
            else:
                self.scheduler_stop_event.set()

            # Clear all task queues
            for task_name in list(self.task_queues.keys()):
                self._clear_task_queue(task_name)

            # Stop all event loops
            for task_name in list(self.event_loops.keys()):
                self._stop_event_loop(task_name)

            # Wait for all scheduler processes to finish
            for task_name in list(self.scheduler_processes.keys()):
                self._join_scheduler_process(task_name)

            # Clean up all task return results
            self.task_results.clear()

            # Reset parameters for scheduler restart
            self.event_loops.clear()
            self.scheduler_processes.clear()
            self.task_queues.clear()

            logger.info(
                f"All schedulers and event loops have stopped, all resources have been released and parameters reset")

    # Task scheduler
    def _scheduler(self, task_name: str) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while not self.scheduler_stop_event.is_set():
            try:
                task = self.task_queues[task_name].get(timeout=1)
            except queue.Empty:
                continue

            # Execute the task after the lock is released
            timeout_processing, task_name, task_id, func, args, kwargs = task
            future = asyncio.run_coroutine_threadsafe(self._execute_task(task), loop)

            with self.scheduler_lock:
                self.running_tasks[task_id] = [future, task_name]
                self.task_counters[task_name] += 1

    # A function that executes a task
    async def _execute_task(self, task: Tuple[bool, str, str, Callable, Tuple, Dict]) -> Any:
        """
        Execute an asynchronous task.
        :param task: Tuple, including timeout processing flag, task name, task ID, task function, positional arguments, and keyword arguments.
        """
        # Unpack task tuple into local variables
        timeout_processing, task_name, task_id, func, args, kwargs = task

        try:
            # Modify the task status
            task_status_manager.add_task_status(task_id, task_name, "running", time.time(), None, None,
                                                timeout_processing)

            logger.info(f"Start running cpu asyncio task | {task_id} | ")

            # If the task needs timeout processing, set the timeout time
            if timeout_processing:
                with ThreadingTimeout(seconds=config["watch_dog_time"] + 5, swallow_exc=False):
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=config["watch_dog_time"]
                    )
            else:
                result = await func(*args, **kwargs)

            # Store task return results, keep up to 2 results
            with self.scheduler_lock:
                if task_id not in self.task_results:
                    self.task_results[task_id] = []
                self.task_results[task_id].append(result)
                if len(self.task_results[task_id]) > 2:
                    self.task_results[task_id].pop(0)  # Remove the oldest result

            # Update task status to "completed"
            task_status_manager.add_task_status(task_id, task_name, "completed", None, time.time(), None,
                                                timeout_processing)

        except (asyncio.TimeoutError, TimeoutException):
            logger.warning(f"Cpu asyncio task | {task_id} | timed out, forced termination")
            task_status_manager.add_task_status(task_id, task_name, "timeout", None, None, None,
                                                timeout_processing)
        except asyncio.CancelledError:
            logger.warning(f"Cpu asyncio task | {task_id} | was cancelled")
            task_status_manager.add_task_status(task_id, task_name, "cancelled", None, None, None,
                                                timeout_processing)
        except Exception as e:
            logger.error(f"Cpu asyncio task | {task_id} | execution failed: {e}")
            task_status_manager.add_task_status(task_id, task_name, "failed", None, None, e,
                                                timeout_processing)
        finally:
            # Opt-out will result in the deletion of the information and the following processing will not be possible
            with self.scheduler_lock:
                if self.task_results.get(task_id, None) is None:
                    return None

                # Remove the task from running tasks dictionary
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]

                # Reduce task counters (ensure it doesn't go below 0)
                if task_name in self.task_counters and self.task_counters[task_name] > 0:
                    self.task_counters[task_name] -= 1

                # Check if all tasks are completed
                if self.task_queues[task_name].empty() and len(self.running_tasks) == 0:
                    self._reset_idle_timer(task_name)

    # The task scheduler closes the countdown
    def _reset_idle_timer(self, task_name: str) -> None:
        """
        Reset the idle timer for a specific task name.

        :param task_name: Task name.
        """
        with self.idle_timer_lock:
            if task_name in self.idle_timers and self.idle_timers[task_name] is not None:
                self.idle_timers[task_name].terminate()
            self.idle_timers[task_name] = multiprocessing.Process(target=self._stop_scheduler,
                                                                  args=(task_name, False, True,))
            self.idle_timers[task_name].start()

    def _cancel_idle_timer(self, task_name: str) -> None:
        """
        Cancel the idle timer for a specific task name.

        :param task_name: Task name.
        """
        with self.idle_timer_lock:
            if task_name in self.idle_timers and self.idle_timers[task_name] is not None:
                self.idle_timers[task_name].terminate()
                del self.idle_timers[task_name]

    def _clear_task_queue(self, task_name: str) -> None:
        """
        Clear the task queue for a specific task name.

        :param task_name: Task name.
        """
        while not self.task_queues[task_name].empty():
            self.task_queues[task_name].get(timeout=1)

    def _join_scheduler_process(self, task_name: str) -> None:
        """
        Wait for the scheduler process to finish for a specific task name.

        :param task_name: Task name.
        """
        if task_name in self.scheduler_processes and self.scheduler_processes[task_name].is_alive():
            self.scheduler_processes[task_name].join()

    def force_stop_task(self, task_id: str) -> bool:
        """
        Force stop a task by its task ID.

        :param task_id: Task ID.
        """
        if task_id in self.running_tasks:
            future = self.running_tasks[task_id][0]
            future.cancel()
            return True
        else:
            logger.warning(f"Cpu asyncio task | {task_id} | does not exist or is already completed")
            return False

    def cancel_all_queued_tasks_by_name(self, task_name: str) -> None:
        """
        Cancel all queued tasks with the same name.

        :param task_name: Task name.
        """
        with self.scheduler_lock:
            if task_name in self.task_queues:
                temp_queue = multiprocessing.Queue()
                while not self.task_queues[task_name].empty():
                    task = self.task_queues[task_name].get()
                    if task[1] == task_name:  # Use function name to match task name
                        logger.warning(
                            f"Cpu asyncio task | {task_name} | is waiting to be executed in the queue, has been deleted")
                    else:
                        temp_queue.put(task)

                # Put uncancelled tasks back into the queue
                while not temp_queue.empty():
                    self.task_queues[task_name].put(temp_queue.get())

    # Obtain the information returned by the corresponding task
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """
        Get the result of a task. If there is a result, return and delete the oldest result; if no result, return None.

        :param task_id: Task ID.
        :return: Task return result, if the task is not completed or does not exist, return None.
        """
        if task_id in self.task_results and self.task_results[task_id]:
            result = self.task_results[task_id].pop(0)  # Return and delete the oldest result
            with self.scheduler_lock:
                if not self.task_results[task_id]:
                    del self.task_results[task_id]
            return result
        return None

    def _cancel_all_running_tasks(self, task_name: str) -> None:
        """
        Forcibly cancel all running tasks for a specific task name.

        :param task_name: Task name.
        """
        with self.scheduler_lock:
            for task_id in list(self.running_tasks.keys()):  # Create a copy using list()
                if self.running_tasks[task_id][1] == task_name:
                    future = self.running_tasks[task_id][0]
                    if not future.done():  # Check if the task is completed
                        future.cancel()
                        logger.warning(f"Cpu asyncio task | {task_id} | has been forcibly cancelled")
                        if task_id in self.task_results:
                            del self.task_results[task_id]

    def _stop_event_loop(self, task_name: str) -> None:
        """
        Stop the event loop for a specific task name.

        :param task_name: Task name.
        """
        if task_name in self.event_loops:
            try:
                # Stop the event loop
                loop = self.event_loops[task_name]
                if loop.is_running():
                    loop.call_soon_threadsafe(loop.stop)
                    if task_name in self.scheduler_processes and self.scheduler_processes[task_name].is_alive():
                        self.scheduler_processes[task_name].join(timeout=1)  # Wait up to 1 second

                # Clean up all tasks and resources
                self._cancel_all_running_tasks(task_name)
                self._clear_task_queue(task_name)
                if task_name in self.task_results:
                    self.task_results[task_name].clear()
                if task_name in self.event_loops:
                    del self.event_loops[task_name]

            except Exception as e:
                logger.error(f"Cpu asyncio task | stopping event loop | error occurred: {e}")
