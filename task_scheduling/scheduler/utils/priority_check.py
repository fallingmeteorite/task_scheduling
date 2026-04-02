# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Task counter with priority-based scheduling capabilities."""
import threading
import random
from typing import Dict, Set, Any, Optional, List, Tuple


class TaskCounter:
    """
    A task counter that tracks high priority tasks and manages paused low priority tasks.
    When a high priority task is added, it automatically pauses a low priority task.
    When a high priority task is removed, it automatically resumes the earliest paused task.
    """

    def __init__(self, task_type: Optional[str] = None):
        """
        Initialize task counter.

        Args:
            task_type: Type of task ('io_liner_task' or 'cpu_liner_task')
        """
        self.high_priority_tasks: Dict[str, Any] = {}  # Track all high priority tasks
        self.task_type = task_type
        self.paused_queue: List[str] = []  # FIFO queue of paused tasks
        self.paused_set: Set[str] = set()  # For fast lookup
        self._lock = threading.Lock()

    def is_high_priority(self, priority: str) -> bool:
        """
        Check if a task has the target high priority level.

        Args:
            priority: Priority string to check

        Returns:
            True if priority matches target priority
        """
        return priority == "high"

    def add_high_priority_task(self, task_id: str, running_tasks: Dict[str, Tuple[Any, str, str]]) -> bool:
        """
        Add a high priority task and automatically pause a low priority task if available.

        Args:
            task_id: Unique identifier for the task
            running_tasks: Dictionary of currently running tasks with their info

        Returns:
            True if task was added successfully, False if no low priority task available to pause
        """
        with self._lock:
            # Find eligible low priority tasks to pause
            eligible_tasks = [
                tid for tid, info in running_tasks.items()
                if not self.is_high_priority(info[2]) and tid not in self.paused_set
            ]

            # If no eligible low priority tasks, cannot add high priority task
            if not eligible_tasks:
                return False

            # Add high priority task to tracking
            self.high_priority_tasks[task_id] = None

            # Randomly select one low priority task to pause
            task_to_pause = random.choice(eligible_tasks)

            from task_scheduling.scheduler.api import pause_api
            pause_api(self.task_type, task_to_pause)
            self.paused_queue.append(task_to_pause)
            self.paused_set.add(task_to_pause)

            return True

    def pause_low_priority_task(self, task_id: str) -> None:
        """
        Pause a specific low priority task and add to queue.

        Args:
            task_id: Task ID to pause
        """
        with self._lock:
            from task_scheduling.scheduler.api import pause_api
            pause_api(self.task_type, task_id)
            self.paused_queue.append(task_id)
            self.paused_set.add(task_id)

    def remove_high_priority_task(self, task_id: str) -> bool:
        """
        Remove a completed high priority task and resume the earliest paused low priority task.

        Args:
            task_id: Task ID of the completed high priority task

        Returns:
            True if task was removed and a task was resumed, False if task not found
        """
        with self._lock:
            if task_id not in self.high_priority_tasks:
                return False

            # Remove the completed high priority task
            del self.high_priority_tasks[task_id]

            # Resume the earliest paused low priority task (FIFO)
            if self.paused_queue:
                from task_scheduling.scheduler.api import resume_api
                task_to_resume = self.paused_queue.pop(0)
                resume_api(self.task_type, task_to_resume)
                self.paused_set.remove(task_to_resume)
                return True

            return True

    def is_high_priority_full(self, max_high_priority_count: int) -> bool:
        """
        Check if the number of high priority tasks has reached the maximum limit.

        Args:
            max_high_priority_count: Maximum allowed high priority tasks

        Returns:
            True if high priority tasks are full, False otherwise
        """
        with self._lock:
            return len(self.high_priority_tasks) >= max_high_priority_count

    def get_high_priority_count(self) -> int:
        """
        Get the current number of high priority tasks.

        Returns:
            Current count of high priority tasks
        """
        with self._lock:
            return len(self.high_priority_tasks)

    def get_paused_queue(self) -> List[str]:
        """
        Get the current paused task queue (for debugging).

        Returns:
            List of paused task IDs in FIFO order
        """
        with self._lock:
            return self.paused_queue.copy()