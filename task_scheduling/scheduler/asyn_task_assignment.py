# -*- coding: utf-8 -*-
import asyncio
import queue
import threading
import time
from typing import Dict, List, Tuple, Callable, Optional, Any

from ..common.config import config
from ..common.log_config import logger
from ..scheduler.memory_release import memory_release_decorator
from ..stopit.threadstop import ThreadingTimeout, TimeoutException


class AsynTask:
    """
    Asynchronous task manager class, responsible for scheduling, executing, and monitoring asynchronous tasks.
    """
    __slots__ = [
        'loop', 'task_queue', 'condition', 'scheduler_lock', 'scheduler_started', 'scheduler_stop_event',
        'task_details', 'running_tasks', 'error_logs', 'scheduler_thread', 'event_loop_thread',
        'banned_task_ids', 'idle_timer', 'idle_timeout', 'idle_timer_lock', 'task_results'
    ]

    def __init__(self) -> None:
        """
        Initialize the asynchronous task manager.
        """
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.task_queue = queue.Queue()  # Task queue
        self.condition = threading.Condition()  # Condition variable for thread synchronization
        self.scheduler_lock = threading.RLock()  # Thread unlock
        self.scheduler_started = False  # Whether the scheduler thread has started
        self.scheduler_stop_event = threading.Event()  # Scheduler thread stop event
        self.task_details: Dict[str, Dict] = {}  # Details of tasks
        self.running_tasks: Dict[str, list[Any]] = {}  # Use weak references to reduce memory usage
        self.error_logs: List[Dict] = []  # Error logs, keep up to 10
        self.scheduler_thread: Optional[threading.Thread] = None  # Scheduler thread
        self.event_loop_thread: Optional[threading.Thread] = None  # Event loop thread
        self.banned_task_ids: List[str] = []  # List of task IDs to be banned
        self.idle_timer: Optional[threading.Timer] = None  # Idle timer
        self.idle_timeout = config["max_idle_time"]  # Idle timeout, default is 60 seconds
        self.idle_timer_lock = threading.Lock()  # Idle timer lock
        self.task_results: Dict[str, List[Any]] = {}  # Store task return results, keep up to 2 results for each task ID

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
                if task_id in self.banned_task_ids:
                    logger.warning(f"Asyncio queue task | {task_id} | is banned and will be deleted")
                    return False

                if self.task_queue.qsize() >= config["maximum_queue_async"]:
                    logger.warning(f"Asyncio queue task | {task_id} | not added, queue is full")
                    logger.warning(f"Asyncio queue is full!!!")
                    return False

                with self.condition:
                    # Store task name in task_details
                    self.task_details[task_id] = {
                        "task_name": task_name,
                        "start_time": None,
                        "status": "pending"
                    }

                self.task_queue.put((timeout_processing, task_name, task_id, func, args, kwargs))

                # If the scheduler thread has not started, start it
                if not self.scheduler_started:
                    self.loop = asyncio.new_event_loop()
                    self.start_scheduler()

                # Cancel the idle timer
                self.cancel_idle_timer()

                with self.condition:
                    self.condition.notify()  # Notify the scheduler thread that a new task is available

                return True
        except Exception as e:
            logger.error(f"Error adding task | {task_id} |: {e}")
            return False

    # Start the scheduler
    def start_scheduler(self) -> None:
        """
        Start the scheduler thread and the event loop thread.
        """
        with self.condition:
            if not self.scheduler_started:
                self.scheduler_started = True
                self.scheduler_thread = threading.Thread(target=self.scheduler, daemon=True)
                self.scheduler_thread.start()

                # Start the event loop thread
                self.event_loop_thread = threading.Thread(target=self.run_event_loop, daemon=True)
                self.event_loop_thread.start()

    # Stop the scheduler
    def stop_scheduler(self, force_cleanup: bool, system_operations: bool = False) -> None:
        """
        :param force_cleanup: Force the end of a running task
        Stop the scheduler and event loop, and forcibly kill all tasks if force_cleanup is True.
        :param system_operations: System execution metrics
        """
        with self.scheduler_lock:
            # Check if all tasks are completed
            if not self.task_queue.empty() or not len(self.running_tasks) == 0:
                if system_operations:
                    logger.warning(f"Asyncio queue task | detected running tasks | stopping operation terminated")
                    return None

            logger.warning("Exit cleanup")

            with self.condition:
                self.scheduler_started = False
                self.scheduler_stop_event.set()
                self.condition.notify_all()

            if force_cleanup:
                # Forcibly cancel all running tasks
                self.cancel_all_running_tasks()
                self.scheduler_stop_event.set()
            else:
                self.scheduler_stop_event.set()

            # Clear the task queue
            self.clear_task_queue()

            # Stop the event loop
            self.stop_event_loop()

            # Wait for the scheduler thread to finish
            self.join_scheduler_thread()

            # Clean up all task return results
            with self.condition:
                self.task_results.clear()

            # Reset parameters for scheduler restart
            self.loop = None
            self.scheduler_thread = None
            self.event_loop_thread = None
            self.banned_task_ids = []
            self.idle_timer = None
            self.error_logs = []

            logger.info(
                "Scheduler and event loop have stopped, all resources have been released and parameters reset")

    # Task scheduler
    def scheduler(self) -> None:
        """
        Scheduler function, fetch tasks from the task queue and submit them to the event loop for execution.
        """
        asyncio.set_event_loop(self.loop)

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

            # Submit the task to the event loop for execution
            future = asyncio.run_coroutine_threadsafe(self.execute_task(task), self.loop)
            with self.condition:
                self.running_tasks[task_id] = [future, task_name]

    # A function that executes a task
    @memory_release_decorator
    async def execute_task(self, task: Tuple[bool, str, str, Callable, Tuple, Dict]) -> Any:
        """
        Execute an asynchronous task.
        :param task: Tuple, including timeout processing flag, task name, task ID, task function, positional arguments, and keyword arguments.
        """
        # Unpack task tuple into local variables
        timeout_processing, task_name, task_id, func, args, kwargs = task

        try:
            if task_id in self.banned_task_ids:
                logger.warning(f"Asyncio queue task | {task_id} | is banned and will be deleted")
                return

            # Modify the task status
            with self.condition:
                self.task_details[task_id]["start_time"] = time.time()
                self.task_details[task_id]["status"] = "running"

            logger.info(f"Start running asyncio queue task | {task_id} | ")

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
            with self.condition:
                if task_id not in self.task_results:
                    self.task_results[task_id] = []
                self.task_results[task_id].append(result)
                if len(self.task_results[task_id]) > 2:
                    self.task_results[task_id].pop(0)  # Remove the oldest result

            # Update task status to "completed"
            with self.condition:
                self.task_details[task_id]["status"] = "completed"

        except asyncio.TimeoutError:
            logger.warning(f"Asyncio queue task | {task_id} | timed out, forced termination")
            with self.condition:
                self.task_details[task_id]["status"] = "timeout"
                self.task_details[task_id]["end_time"] = 'NaN'
        except TimeoutException:
            logger.warning(f"Asyncio queue task | {task_id} | timed out, forced termination")
            with self.condition:
                self.task_details[task_id]["status"] = "timeout"
                self.task_details[task_id]["end_time"] = 'NaN'
        except asyncio.CancelledError:
            logger.warning(f"Asyncio queue task | {task_id} | was cancelled")
            with self.condition:
                self.task_details[task_id]["status"] = "cancelled"
        except Exception as e:
            logger.error(f"Asyncio queue task | {task_id} | execution failed: {e}")
            with self.condition:
                self.task_details[task_id]["status"] = "failed"
                self.log_error(task_id, e)
        finally:
            # Opt-out will result in the deletion of the information and the following processing will not be possible
            with self.condition:
                if self.task_details.get(task_id, None) is None:
                    return None

                if not self.task_details[task_id].get("end_time") == "NaN":
                    self.task_details[task_id]["end_time"] = time.time()

                # Remove the task from running tasks dictionary
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]

                # Check if all tasks are completed
                if self.task_queue.empty() and len(self.running_tasks) == 0:
                    self.reset_idle_timer()

    # Log error information during task execution
    def log_error(self, task_id: str, exception: Exception) -> None:
        """
        Log error information during task execution.

        :param task_id: Task ID.
        :param exception: Exception object.
        """
        error_info = {
            "task_id": task_id,
            "error_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "error_message": str(exception)
        }
        with self.condition:
            self.error_logs.append(error_info)
            # If error logs exceed 10, remove the earliest one
            if len(self.error_logs) > 10:
                self.error_logs.pop(0)

    # The task scheduler closes the countdown
    def reset_idle_timer(self) -> None:
        """
        Reset the idle timer.
        """
        with self.idle_timer_lock:
            if self.idle_timer is not None:
                self.idle_timer.cancel()
            self.idle_timer = threading.Timer(self.idle_timeout, self.stop_scheduler, args=(False, True,))
            self.idle_timer.start()

    def cancel_idle_timer(self) -> None:
        """
        Cancel the idle timer.
        """
        with self.idle_timer_lock:
            if self.idle_timer is not None:
                self.idle_timer.cancel()
                self.idle_timer = None

    def clear_task_queue(self) -> None:
        """
        Clear the task queue.
        """
        while not self.task_queue.empty():
            self.task_queue.get()

    def join_scheduler_thread(self) -> None:
        """
        Wait for the scheduler thread to finish.
        """
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join()

    def get_queue_info(self) -> Dict:
        """
        Get detailed information about the task queue.

        Returns:
            Dict: Dictionary containing queue size, number of running tasks, number of failed tasks, task details, and error logs.
        """
        with self.condition:
            queue_info = {
                "queue_size": self.task_queue.qsize(),
                "running_tasks_count": 0,
                "failed_tasks_count": 0,
                "task_details": {},
                "error_logs": self.error_logs.copy()  # Return recent error logs
            }

            for task_id, details in self.task_details.items():
                status = details.get("status")
                task_name = details.get("task_name", "Unknown")
                if status == "running":
                    start_time = details.get("start_time")
                    current_time = time.time()
                    if current_time - start_time > config["watch_dog_time"]:
                        # Change end time of timed out tasks to NaN
                        queue_info["task_details"][task_id] = {
                            "task_name": task_name,
                            "start_time": start_time,
                            "status": status,
                            "end_time": "NaN"
                        }
                    else:
                        queue_info["task_details"][task_id] = details
                    queue_info["running_tasks_count"] += 1
                elif status == "failed":
                    queue_info["task_details"][task_id] = details
                    queue_info["failed_tasks_count"] += 1
                else:
                    queue_info["task_details"][task_id] = details
        return queue_info

    def force_stop_task(self, task_id: str) -> None:
        """
        Force stop a task by its task ID.

        :param task_id: Task ID.
        """
        with self.condition:
            if task_id in self.running_tasks:
                future = self.running_tasks[task_id][0]
                future.cancel()
                logger.warning(f"Asyncio queue task | {task_id} | has been forcibly cancelled")
            else:
                logger.warning(f"Asyncio queue task | {task_id} | does not exist or is already completed")

    def cancel_all_queued_tasks_by_name(self, task_name: str) -> None:
        """
        Cancel all queued tasks with the same name.

        :param task_name: Task name.
        """
        with self.condition:
            temp_queue = queue.Queue()
            while not self.task_queue.empty():
                task = self.task_queue.get()
                if task[2] == task_name:  # Use function name to match task name
                    logger.warning(
                        f"Asyncio queue task | {task_name} | is waiting to be executed in the queue, has been deleted")
                    # Clean up task details and results
                    if task[2] in self.task_details:  # Use task ID to delete task details and results
                        del self.task_details[task[2]]
                    if task[2] in self.task_results:
                        del self.task_results[task[2]]
                else:
                    temp_queue.put(task)

            # Put uncancelled tasks back into the queue
            while not temp_queue.empty():
                self.task_queue.put(temp_queue.get())

    def cancel_all_queued_tasks(self, task_name: str) -> None:
        """
        Cancel all queued tasks with the banned task name.

        :param task_name: Task name.
        """
        with self.condition:
            temp_queue = queue.Queue()
            while not self.task_queue.empty():
                task = self.task_queue.get()
                if task[2] == task_name:
                    logger.warning(
                        f"Asyncio queue task | {task_name} | is waiting to be executed in the queue, has been deleted")
                    # Clean up task details and results
                    if task[2] in self.task_details:
                        del self.task_details[task[2]]
                    if task[2] in self.task_results:
                        del self.task_results[task[2]]
                else:
                    temp_queue.put(task)

            # Put uncancelled tasks back into the queue
            while not temp_queue.empty():
                self.task_queue.put(temp_queue.get())

    def ban_task_name(self, task_name: str) -> None:
        """
        Ban a task name from execution, delete tasks directly if detected and print information.

        :param task_name: Task name.
        """
        with self.condition:
            self.banned_task_ids.append(task_name)
            logger.warning(f"Asyncio queue task | {task_name} | has been banned from execution")

            # Cancel all queued tasks with the banned task name
            self.cancel_all_queued_tasks_by_name(task_name)

    def allow_task_name(self, task_name: str) -> None:
        """
        Allow a banned task name to be executed again.

        :param task_name: Task name.
        """
        with self.condition:
            if task_name in self.banned_task_ids:
                self.banned_task_ids.remove(task_name)
                logger.info(f"Asyncio queue task | {task_name} | is allowed for execution")
            else:
                logger.warning(f"Asyncio queue task | {task_name} | is not banned, no action taken")

    # Obtain the information returned by the corresponding task
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """
        Get the result of a task. If there is a result, return and delete the oldest result; if no result, return None.

        :param task_id: Task ID.
        :return: Task return result, if the task is not completed or does not exist, return None.
        """
        if task_id in self.task_results and self.task_results[task_id]:
            result = self.task_results[task_id].pop(0)  # Return and delete the oldest result
            with self.condition:
                if not self.task_results[task_id]:
                    del self.task_results[task_id]
            return result
        logger.warning(f"Asyncio queue task | {task_id} | does not exist or has been completed and removed")
        return None

    def run_event_loop(self) -> None:
        """
        Run the event loop.
        """
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def cancel_all_running_tasks(self) -> None:
        """
        Forcibly cancel all running tasks.
        """
        with self.condition:
            for task_id in list(self.running_tasks.keys()):  # Create a copy using list()
                future = self.running_tasks[task_id][0]
                if not future.done():  # Check if the task is completed
                    future.cancel()
                    logger.warning(f"Asyncio queue task | {task_id} | has been forcibly cancelled")
                    # Update task status to "cancelled"
                    if task_id in self.task_details:
                        self.task_details[task_id]["status"] = "cancelled"
                        self.task_details[task_id]["end_time"] = time.time()
                    if task_id in self.task_results:
                        del self.task_results[task_id]

    def stop_event_loop(self) -> None:
        """
        Stop the event loop.
        """
        if self.loop and self.loop.is_running():  # Ensure the event loop is running
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
                # Wait for the event loop thread to finish
                if self.event_loop_thread and self.event_loop_thread.is_alive():
                    self.event_loop_thread.join(timeout=1)  # Wait up to 1 second
                # Clean up all tasks and resources
                self.cancel_all_running_tasks()
                self.clear_task_queue()
                with self.condition:
                    self.task_details.clear()
                    self.task_results.clear()
            except Exception as e:
                logger.error(f"Asyncio queue task | stopping event loop | error occurred: {e}")

    def check_and_log_task_details(self) -> None:
        """
        Check if the number of task details exceeds the configured limit and remove those with specific statuses.
        """
        with self.condition:
            task_details_copy = self.task_details.copy()
            if len(task_details_copy) > config["maximum_task_info_storage"]:
                logger.warning(f"More than {config['maximum_task_info_storage']} task details detected. "
                               f"Cleaning up old task details.")

                # Filter out tasks with status 'failed', 'completed', or 'timeout'
                new_task_details = {task_id: details for task_id, details in task_details_copy.items()
                                    if details.get("status") in ["pending", "running"]}

                # Update the task details with the filtered results
                self.task_details = new_task_details

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        Obtain task status information for a specified task_id.

        :param task_id: Task ID.
        :return: A dictionary containing information about the status of the task, or None if the task does not exist.
        """
        if task_id in self.task_details:
            return self.task_details[task_id]
        else:
            logger.warning(f"Asyncio queue task | {task_id} | does not exist or has been completed and removed.")
            return None


# Instantiate object
asyntask = AsynTask()
