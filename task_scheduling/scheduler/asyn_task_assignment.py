import asyncio
import queue
import threading
import time
from typing import Dict, List, Tuple, Callable, Optional, Any
from weakref import WeakValueDictionary

from ..common.config import config
from ..common.logging import logger
from ..scheduler.memory_release import memory_release_decorator
from ..stopit.threadstop import ThreadingTimeout, TimeoutException


class AsynTask:
    """
    Asynchronous task manager class, responsible for scheduling, executing, and monitoring asynchronous tasks.
    """
    __slots__ = [
        'loop', 'task_queue', 'condition', 'scheduler_started', 'scheduler_stop_event',
        'task_details', 'running_tasks', 'error_logs', 'scheduler_thread', 'event_loop_thread',
        'banned_task_ids', 'idle_timer', 'idle_timeout', 'idle_timer_lock', 'task_results', 'thread_local_data'
    ]

    def __init__(self) -> None:
        """
        Initialize the asynchronous task manager.
        """
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.task_queue = queue.Queue()  # Task queue
        self.condition = threading.Condition()  # Condition variable for thread synchronization
        self.scheduler_started = False  # Whether the scheduler thread has started
        self.scheduler_stop_event = threading.Event()  # Scheduler thread stop event
        self.task_details: Dict[str, Dict] = {}  # Details of tasks
        self.running_tasks: WeakValueDictionary[
            str, asyncio.Task] = WeakValueDictionary()  # Use weak references to reduce memory usage
        self.error_logs: List[Dict] = []  # Error logs, keep up to 10
        self.scheduler_thread: Optional[threading.Thread] = None  # Scheduler thread
        self.event_loop_thread: Optional[threading.Thread] = None  # Event loop thread
        self.banned_task_ids: List[str] = []  # List of task IDs to be banned
        self.idle_timer: Optional[threading.Timer] = None  # Idle timer
        self.idle_timeout = config["max_idle_time"]  # Idle timeout, default is 60 seconds
        self.idle_timer_lock = threading.Lock()  # Idle timer lock
        self.task_results: Dict[str, List[Any]] = {}  # Store task return results, keep up to 2 results for each task ID
        self.thread_local_data = threading.local()  # Thread-local data storage

    def reset_idle_timer(self) -> None:
        """
        Reset the idle timer.
        """
        with self.idle_timer_lock:
            if self.idle_timer is not None:
                self.idle_timer.cancel()
            self.idle_timer = threading.Timer(self.idle_timeout, self.stop_scheduler)
            self.idle_timer.start()

    def cancel_idle_timer(self) -> None:
        """
        Cancel the idle timer.
        """
        with self.idle_timer_lock:
            if self.idle_timer is not None:
                self.idle_timer.cancel()
                self.idle_timer = None

    @memory_release_decorator
    async def execute_task(self, task: Tuple[bool, str, Callable, Tuple, Dict]) -> None:
        """
        Execute an asynchronous task
        :param task: Task tuple, including timeout processing flag, task ID, task function, positional arguments, and keyword arguments.
        """
        # Store task data in thread-local storage
        self.thread_local_data.timeout_processing, self.thread_local_data.task_id, self.thread_local_data.func, self.thread_local_data.args, self.thread_local_data.kwargs = task
        logger.debug(f"Start running asynchronous task, task name: {self.thread_local_data.task_id}")

        try:
            if self.thread_local_data.task_id in self.banned_task_ids:
                logger.warning(f"Task {self.thread_local_data.task_id} is banned and will be deleted")
                return

            self.task_details[self.thread_local_data.task_id] = {
                "start_time": time.monotonic(),
                "status": "running"
            }

            # If the task needs timeout processing, set the timeout time
            if self.thread_local_data.timeout_processing:
                with ThreadingTimeout(seconds=config["watch_dog_time"], swallow_exc=False):
                    result = await asyncio.wait_for(
                        self.thread_local_data.func(*self.thread_local_data.args, **self.thread_local_data.kwargs),
                        timeout=config["watch_dog_time"])
            else:
                result = await self.thread_local_data.func(*self.thread_local_data.args,
                                                           **self.thread_local_data.kwargs)

            # Store task return results, keep up to 2 results
            with self.condition:
                if self.thread_local_data.task_id not in self.task_results:
                    self.task_results[self.thread_local_data.task_id] = []
                self.task_results[self.thread_local_data.task_id].append(result)
                if len(self.task_results[self.thread_local_data.task_id]) > 2:
                    self.task_results[self.thread_local_data.task_id].pop(0)  # Remove the oldest result

            # Update task status to "completed"
            self.task_details[self.thread_local_data.task_id]["status"] = "completed"

        except asyncio.TimeoutError:
            logger.warning(f"Queue task | {self.thread_local_data.task_id} | timed out, forced termination")
            self.task_details[self.thread_local_data.task_id]["status"] = "timeout"
        except TimeoutException:
            logger.warning(f"Queue task | {self.thread_local_data.task_id} | timed out, forced termination")
            self.task_details[self.thread_local_data.task_id]["status"] = "timeout"
        except asyncio.CancelledError:
            logger.warning(f"Queue task | {self.thread_local_data.task_id} | was cancelled")
            self.task_details[self.thread_local_data.task_id]["status"] = "cancelled"
        except Exception as e:
            logger.error(f"Asynchronous task {self.thread_local_data.task_id} execution failed: {e}")
            self.task_details[self.thread_local_data.task_id]["status"] = "failed"
            self.log_error(self.thread_local_data.task_id, e)
        finally:
            self.task_details[self.thread_local_data.task_id]["end_time"] = time.monotonic()
            # Remove the task from running tasks dictionary
            if self.thread_local_data.task_id in self.running_tasks:
                del self.running_tasks[self.thread_local_data.task_id]

            # Check if all tasks are completed
            if self.task_queue.empty() and len(self.running_tasks) == 0:
                self.reset_idle_timer()
            # Explicitly delete temporary variables in task
            del self.thread_local_data.timeout_processing
            del self.thread_local_data.task_id
            del self.thread_local_data.func
            del self.thread_local_data.args
            del self.thread_local_data.kwargs

    def get_task_result(self, task_id: str) -> Optional[Any]:
        """
        Get the result of a task. If there is a result, return and delete the oldest result; if no result, return None.

        :param task_id: Task ID.
        :return: Task return result, if the task is not completed or does not exist, return None.
        """
        with self.condition:
            if task_id in self.task_results and self.task_results[task_id]:
                return self.task_results[task_id].pop(0)  # Return and delete the oldest result
            return None

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
                task_id = task[1]

                # Check if task ID is banned
                if task_id in self.banned_task_ids:
                    logger.warning(f"Task {task_id} is banned and will be deleted")
                    self.task_queue.task_done()
                    continue

                # Submit the task to the event loop for execution
                future = asyncio.run_coroutine_threadsafe(self.execute_task(task), self.loop)
                self.running_tasks[task_id] = future

            # Check if running tasks have timed out
            self.check_running_tasks_timeout()

            # Wait for a while before checking again
            time.sleep(config["scheduler_check_interval"])

    def check_running_tasks_timeout(self) -> None:
        """
        Check if running tasks have timed out.
        """
        current_time = time.monotonic()
        for task_id, details in list(self.task_details.items()):  # Create a copy using list()
            if details.get("status") == "running":
                start_time = details.get("start_time")
                if current_time - start_time > config["watch_dog_time"]:
                    logger.warning(f"Queue task | {task_id} | timed out, but continues to run")
                    # Do not cancel the task, just record the timeout
                    self.task_details[task_id]["status"] = "running"

    def add_task(self, timeout_processing: bool, task_id: str, func: Callable, *args, **kwargs) -> None:
        """
        Add a task to the task queue.

        :param timeout_processing: Whether to enable timeout processing.
        :param task_id: Task ID.
        :param func: Task function.
        :param args: Positional arguments for the task function.
        :param kwargs: Keyword arguments for the task function.

        """
        if task_id in self.banned_task_ids:
            logger.warning(f"Task {task_id} is banned and will be deleted")
            return

        if self.task_queue.qsize() <= config["maximum_queue_async"]:
            self.task_queue.put((timeout_processing, task_id, func, args, kwargs))

            # If the scheduler thread has not started, start it
            if not self.scheduler_started:
                self.loop = asyncio.new_event_loop()
                self.start_scheduler()

            # Cancel the idle timer
            self.cancel_idle_timer()

            # Notify the scheduler thread of a new task
            with self.condition:
                self.condition.notify()
        else:
            logger.warning(f"Task {task_id} not added, queue is full")

    def start_scheduler(self) -> None:
        """
        Start the scheduler thread and the event loop thread.
        """
        self.scheduler_started = True
        self.scheduler_thread = threading.Thread(target=self.scheduler, daemon=True)
        self.scheduler_thread.start()

        # Start the event loop thread
        self.event_loop_thread = threading.Thread(target=self.run_event_loop, daemon=True)
        self.event_loop_thread.start()

    def run_event_loop(self) -> None:
        """
        Run the event loop.
        """
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def stop_scheduler(self) -> None:
        """
        Stop the scheduler and event loop, and forcibly kill all tasks.
        """
        logger.warning("Exit cleanup")
        self.scheduler_started = False
        self.scheduler_stop_event.set()
        with self.condition:
            self.condition.notify_all()

        # Forcibly cancel all running tasks
        self.cancel_all_running_tasks()

        # Clear the task queue
        self.clear_task_queue()

        # Stop the event loop
        self.stop_event_loop()

        # Wait for the scheduler thread to finish
        self.join_scheduler_thread()

        # Clean up all task return results
        self.task_results.clear()

        # Reset parameters for scheduler restart
        self.loop = None
        self.scheduler_thread = None
        self.event_loop_thread = None
        self.banned_task_ids = []
        self.idle_timer = None
        self.error_logs = []

        logger.info("Scheduler and event loop have stopped, all resources have been released and parameters reset")

    def cancel_all_running_tasks(self) -> None:
        """
        Forcibly cancel all running tasks.
        """
        for task_id in list(self.running_tasks.keys()):  # Create a copy using list()
            future = self.running_tasks[task_id]
            if not future.done():  # Check if the task is completed
                future.cancel()
                logger.warning(f"Task {task_id} has been forcibly cancelled")
                # Update task status to "cancelled"
                self.task_details[task_id]["status"] = "cancelled"
                self.task_details[task_id]["end_time"] = time.monotonic()

    def clear_task_queue(self) -> None:
        """
        Clear the task queue.
        """
        while not self.task_queue.empty():
            self.task_queue.get()

    def stop_event_loop(self) -> None:
        """
        Stop the event loop.
        """
        if self.loop and self.loop.is_running():  # Ensure the event loop is running
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
                # Wait for the event loop thread to finish
                if self.event_loop_thread and self.event_loop_thread.is_alive():
                    self.event_loop_thread.join(timeout=5)  # Wait up to 5 seconds
            except Exception as e:
                logger.error(f"Error occurred while stopping the event loop: {e}")

    def join_scheduler_thread(self) -> None:
        """
        Wait for the scheduler thread to finish.
        """
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)  # Wait up to 5 seconds

    def get_queue_info(self) -> Dict:
        """
        Get detailed information about the task queue.

        Returns:
            Dict: Dictionary containing queue size, number of running tasks, number of failed tasks, task details, and error logs.
        """
        with self.condition:
            current_time = time.monotonic()
            queue_info = {
                "queue_size": self.task_queue.qsize(),
                "running_tasks_count": 0,
                "failed_tasks_count": 0,
                "task_details": {},
                "error_logs": self.error_logs.copy()  # Return recent error logs
            }

            for task_id, details in self.task_details.items():
                status = details.get("status")
                if status == "running":
                    start_time = details.get("start_time")
                    if current_time - start_time > config["watch_dog_time"]:
                        # Change end time of timed out tasks to NaN
                        queue_info["task_details"][task_id] = {
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
        if task_id in self.running_tasks:
            future = self.running_tasks[task_id]
            future.cancel()
            logger.warning(f"Task {task_id} has been forcibly cancelled")
        else:
            logger.warning(f"Task {task_id} does not exist or is already completed")

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

    def cancel_all_queued_tasks_by_name(self, task_name: str) -> None:
        """
        Cancel all queued tasks with the same name.

        :param task_name: Task name.
        """
        with self.condition:
            temp_queue = queue.Queue()
            while not self.task_queue.empty():
                task = self.task_queue.get()
                if task[1] == task_name:
                    logger.warning(f"Task {task_name} is waiting to be executed in the queue, has been deleted")
                else:
                    temp_queue.put(task)

            # Put uncancelled tasks back into the queue
            while not temp_queue.empty():
                self.task_queue.put(temp_queue.get())

    def ban_task_id(self, task_id: str) -> None:
        """
        Ban a task ID from execution, delete tasks directly if detected and print information.

        :param task_id: Task ID.
        """
        with self.condition:
            self.banned_task_ids.append(task_id)
            logger.warning(f"Task ID {task_id} has been banned from execution")

            # Cancel all queued tasks with the banned task ID
            self.cancel_all_queued_tasks(task_id)

    def cancel_all_queued_tasks(self, task_id: str) -> None:
        """
        Cancel all queued tasks with the banned task ID.

        :param task_id: Task ID.
        """
        with self.condition:
            temp_queue = queue.Queue()
            while not self.task_queue.empty():
                task = self.task_queue.get()
                if task[1] == task_id:
                    logger.warning(f"Task ID {task_id} is waiting to be executed in the queue, has been deleted")
                else:
                    temp_queue.put(task)

            # Put uncancelled tasks back into the queue
            while not temp_queue.empty():
                self.task_queue.put(temp_queue.get())


# Instantiate object
asyntask = AsynTask()
