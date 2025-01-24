import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from functools import partial
from typing import Callable, Dict, List, Tuple, Optional, Any
from weakref import WeakValueDictionary

from ..common.config import config
from ..common.log_config import logger
from ..scheduler.memory_release import memory_release_decorator
from ..stopit.task_destruction import task_manager
from ..stopit.threadstop import ThreadingTimeout, TimeoutException


class LineTask:
    """
    Linear task manager class, responsible for managing the scheduling, execution, and monitoring of linear tasks.
    """
    __slots__ = [
        'task_queue', 'running_tasks', 'task_details', 'lock', 'condition',
        'scheduler_started', 'scheduler_stop_event', 'error_logs', 'scheduler_thread',
        'banned_task_ids', 'idle_timer', 'idle_timeout', 'idle_timer_lock', 'task_results'
    ]

    def __init__(self) -> None:
        self.task_queue = queue.Queue()  # Task queue
        self.running_tasks: WeakValueDictionary[str, Future] = WeakValueDictionary()  # Running tasks
        self.task_details: Dict[str, Dict] = {}  # Task details
        self.lock = threading.Lock()  # Lock to protect access to shared resources
        self.condition = threading.Condition()  # Condition variable for thread synchronization
        self.scheduler_started = False  # Whether the scheduler thread has started
        self.scheduler_stop_event = threading.Event()  # Scheduler thread stop event
        self.error_logs: List[Dict] = []  # Error logs, keep up to 10
        self.scheduler_thread: Optional[threading.Thread] = None  # Scheduler thread
        self.banned_task_ids: List[str] = []  # List of banned task IDs
        self.idle_timer: Optional[threading.Timer] = None  # Idle timer
        self.idle_timeout = config["max_idle_time"]  # Idle timeout, default is 60 seconds
        self.idle_timer_lock = threading.Lock()  # Idle timer lock
        self.task_results: Dict[str, List[Any]] = {}  # Store task return results, keep up to 2 results for each task ID

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
    def execute_task(self, task: Tuple[bool, str, Callable, Tuple, Dict]) -> Any:
        """
        Execute a linear task.

        :param task: Task tuple, including timeout processing flag, task ID, task function, positional arguments, and keyword arguments.
        """
        timeout_processing, task_id, func, args, kwargs = task
        try:
            if task_id in self.banned_task_ids:
                logger.warning(f"Task {task_id} is banned and will be deleted")
                return

            with self.lock:
                self.task_details[task_id] = {
                    "start_time": time.time(),
                    "status": "running",
                    "timeout_processing": timeout_processing  # Add this line to record timeout_processing flag
                }

            logger.info(f"Start running linear task, task name: {task_id}")
            if timeout_processing:
                with ThreadingTimeout(seconds=config["watch_dog_time"], swallow_exc=False) as task_control:
                    task_manager.add(task_control, task_id)
                    return_results = func(*args, **kwargs)
                    task_manager.remove(task_id)
            else:
                with ThreadingTimeout(seconds=None, swallow_exc=True) as task_control:
                    task_manager.add(task_control, task_id)
                    return_results = func(*args, **kwargs)
                    task_manager.remove(task_id)
        except TimeoutException:
            logger.warning(f"Linear queue task | {task_id} | timed out, forced termination")
            self.update_task_status(task_id, "timeout")
            raise  # Re-raise the exception to be handled by the task_done callback
        except Exception as e:
            logger.error(f"Linear task {task_id} execution failed: {e}")
            self.log_error(task_id, e)
            raise  # Re-raise the exception to be handled by the task_done callback
        finally:
            if task_manager.check(task_id):
                task_manager.remove(task_id)
                # Define variables when they are not defined
                return_results = "error happen"
                return return_results

            else:
                return return_results

    def scheduler(self) -> None:
        """
        Scheduler function, fetch tasks from the task queue and submit them to the thread pool for execution.
        """
        with ThreadPoolExecutor(max_workers=int(config["line_task_max"])) as executor:
            while not self.scheduler_stop_event.is_set():
                with self.condition:
                    while self.task_queue.empty() and not self.scheduler_stop_event.is_set():
                        self.condition.wait()

                    if self.scheduler_stop_event.is_set():
                        break

                    if self.task_queue.qsize() == 0:
                        continue

                    task = self.task_queue.get()

                timeout_processing, task_id, func, args, kwargs = task

                with self.lock:
                    if task_id in self.banned_task_ids:
                        logger.warning(f"Task {task_id} is banned and will be deleted")
                        self.task_queue.task_done()
                        continue

                    if task_id in self.running_tasks:
                        self.task_queue.put(task)
                        continue

                    future = executor.submit(self.execute_task, task)
                    self.running_tasks[task_id] = future
                    self.task_details[task_id] = {
                        "start_time": time.time(),
                        "status": "running"
                    }

                future.add_done_callback(partial(self.task_done, task_id))
                # Start a thread to monitor the state of the future
                threading.Thread(target=self.monitor_future_timeout, args=(task_id, timeout_processing,)).start()

    def monitor_future_timeout(self, task_id: str, timeout_processing: bool) -> None:
        if not timeout_processing:
            return None
        seconds = config["watch_dog_time"] + 5
        while seconds > 0:
            time.sleep(1)
            seconds -= 1
            with self.lock:
                if not self.task_details[task_id]["status"] == "running":
                    return None
        # If the timeout cannot be processed, the task is forcibly terminated
        # !!! dangerous
        task_manager.force_stop(task_id)
        return None

    def task_done(self, task_id: str, future: Future) -> None:
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
            if not result == "error happen":
                self.update_task_status(task_id, "completed")

        except TimeoutException as e:
            logger.error(f"Linear task {task_id} timed out: {e}")
            self.update_task_status(task_id, "timeout")
            self.log_error(task_id, e)
        except Exception as e:
            logger.error(f"Linear task {task_id} execution failed: {e}")
            self.update_task_status(task_id, "failed")
            self.log_error(task_id, e)
        finally:
            # Ensure the Future object is deleted
            with self.lock:
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]

            # Check if all tasks are completed
            with self.lock:
                if self.task_queue.empty() and len(self.running_tasks) == 0:
                    self.reset_idle_timer()

    def update_task_status(self, task_id: str, status: str) -> None:
        """
        Update task status.

        :param task_id: Task ID.
        :param status: Task status.
        """
        with self.lock:
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            if task_id in self.task_details:
                self.task_details[task_id]["status"] = status
                # Set end_time to NaN if the task failed because of timeout and timeout_processing was False
                if status == "timeout":
                    self.task_details[task_id]["end_time"] = "NaN"
                else:
                    self.task_details[task_id]["end_time"] = time.time()

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
        with self.lock:
            self.error_logs.append(error_info)
            if len(self.error_logs) > 10:
                self.error_logs.pop(0)

    def add_task(self, timeout_processing: bool, task_id: str, func: Callable, *args, **kwargs) -> bool:
        """
        Add a task to the task queue.

        :param timeout_processing: Whether to enable timeout processing.
        :param task_id: Task ID.
        :param func: Task function.
        :param args: Positional arguments for the task function.
        :param kwargs: Keyword arguments for the task function.
        :return: True if the task was successfully added, False otherwise.
        """
        if task_id in self.banned_task_ids:
            logger.warning(f"Task {task_id} is banned and will be deleted")
            return False

        if self.task_queue.qsize() <= config["maximum_queue_line"]:
            self.task_queue.put((timeout_processing, task_id, func, args, kwargs))

            if not self.scheduler_started:
                self.start_scheduler()

            with self.condition:
                self.condition.notify()

            # Cancel the idle timer
            self.cancel_idle_timer()
            return True
        else:
            logger.warning(f"Task {task_id} not added, queue is full")
            return False

    def start_scheduler(self) -> None:
        """
        Start the scheduler thread.
        """
        self.scheduler_started = True
        self.scheduler_thread = threading.Thread(target=self.scheduler, daemon=True)
        self.scheduler_thread.start()

    def stop_scheduler(self) -> None:
        """
        Stop the scheduler thread and forcibly kill all tasks.
        """
        logger.warning("Exit cleanup")
        task_manager.force_stop_all()
        self.scheduler_stop_event.set()
        with self.condition:
            self.condition.notify_all()

        self.cancel_all_running_tasks()
        self.clear_task_queue()
        self.join_scheduler_thread()

        # Reset parameters for scheduler restart
        self.scheduler_started = False
        self.scheduler_stop_event.clear()
        self.error_logs = []
        self.scheduler_thread = None
        self.banned_task_ids = []
        self.idle_timer = None
        self.task_results = {}

        logger.info("Scheduler thread has stopped, all resources have been released and parameters reset")

    def cancel_all_running_tasks(self) -> None:
        """
        Forcibly cancel all running tasks.
        """
        with self.lock:
            for task_id, future in self.running_tasks.items():
                task_manager.force_stop(task_id)
                future.cancel()
                logger.warning(f"Task {task_id} has been forcibly cancelled")
                self.update_task_status(task_id, "cancelled")

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
            Dict: Dictionary containing queue size, number of running tasks, task details, and error logs.
        """
        with self.lock:
            queue_info = {
                "queue_size": self.task_queue.qsize(),
                "running_tasks_count": len(self.running_tasks),
                "task_details": self.task_details.copy(),
                "error_logs": self.error_logs.copy()
            }
            return queue_info

    def force_stop_task(self, task_id: str) -> None:
        """
        Force stop a task by its task ID.

        :param task_id: Task ID.
        """
        with self.lock:
            if task_id in self.running_tasks:
                task_manager.force_stop(task_id)
                future = self.running_tasks[task_id]
                future.cancel()
                logger.warning(f"Task {task_id} has been forcibly cancelled")
                self.update_task_status(task_id, "cancelled")
            else:
                logger.warning(f"Task {task_id} does not exist or is already completed")

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
        with self.lock:
            self.banned_task_ids.append(task_id)
            logger.warning(f"Task ID {task_id} has been banned from execution")

            # Cancel all queued tasks with the banned task ID
            self.cancel_all_queued_tasks(task_id)

            # Cancel any running tasks with the banned task ID
            if task_id in self.running_tasks:
                self.force_stop_task(task_id)

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

    def allow_task_id(self, task_id: str) -> None:
        """
        Allow a banned task ID to be executed again.

        :param task_id: Task ID.
        """
        with self.lock:
            if task_id in self.banned_task_ids:
                self.banned_task_ids.remove(task_id)
                logger.info(f"Task ID {task_id} has been allowed for execution")
            else:
                logger.warning(f"Task ID {task_id} is not banned, no action taken")

    def get_task_result(self, task_id: str) -> Optional[Any]:
        """
        Get the result of a task. If there is a result, return and delete the oldest result; if no result, return None.

        :param task_id: Task ID.
        :return: Task return result, if the task is not completed or does not exist, return None.
        """
        with self.lock:
            if task_id in self.task_results and self.task_results[task_id]:
                result = self.task_results[task_id].pop(0)  # Return and delete the oldest result
                if not self.task_results[task_id]:
                    del self.task_results[task_id]
                return result
            return None


# Instantiate object
linetask = LineTask()
