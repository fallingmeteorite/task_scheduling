# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import random
from typing import Callable, Dict, Set, Tuple, Any, Optional


class TaskCounter:
    """
    A task counter with scheduling capabilities for managing task preemption
    based on priority levels. Supports pausing and resuming low-priority tasks
    when high-priority tasks require resources.
    """

    def __init__(self, task_type: Optional[str] = None):
        """
        Initialize task counter with tracking capabilities.

        Args:
            task_type: Type of task ('io_liner_task' or 'cpu_liner_task')
        """
        self.last_running_tasks: Dict[str, Tuple[Any, str, str]] = {}
        self.target_priority = "high"
        self.task_type = task_type
        self.paused_tasks: Set[str] = set()
        self.count = 0

    def add_count(self, max_count: int) -> bool:
        """
        Increment task count if within maximum limit.

        Args:
            max_count: Maximum allowed task count

        Returns:
            bool: True if count was successfully added, False if limit reached
        """
        if self.count >= max_count:
            return False

        self.count += 1
        return True

    def reduce_count(self) -> None:
        """
        Decrement task count, ensuring it doesn't go below zero.
        """
        self.count = max(0, self.count - 1)

    def is_high_priority(self, priority: str) -> bool:
        """
        Check if a task has the target high priority level.

        Args:
            priority: Priority string to check

        Returns:
            bool: True if priority matches target priority
        """
        return priority == self.target_priority

    def schedule_tasks(self,
                       running_tasks: Dict[str, Tuple[Any, str, str]],
                       pause_task: Callable,
                       resume_task: Callable) -> None:
        """
        Main scheduling function that manages task preemption based on priority.

        1. Monitors current running tasks
        2. Pauses low-priority tasks when high-priority tasks appear
        3. Resumes low-priority tasks when high-priority tasks complete

        Args:
            running_tasks: Dictionary of currently running tasks {task_id: (future, task_name, priority)}
            pause_task: Callback function to pause tasks
            resume_task: Callback function to resume tasks
        """
        # Count current high-priority tasks
        current_high_count = sum(
            1 for task_info in running_tasks.values()
            if self.is_high_priority(task_info[2])
        )

        # Compare with previous count to detect changes
        previous_high_count = sum(
            1 for task_info in self.last_running_tasks.values()
            if self.is_high_priority(task_info[2])
        )

        delta = current_high_count - previous_high_count

        if delta > 0:
            # High-priority tasks increased - pause low-priority tasks
            self._pause_low_priority_tasks(running_tasks, delta, pause_task)
        elif delta < 0:
            # High-priority tasks decreased - resume low-priority tasks
            self._resume_low_priority_tasks(abs(delta), resume_task)

        # Update tracking of high-priority tasks for next comparison
        self._update_high_priority_tracking(running_tasks)

    def _update_high_priority_tracking(self, running_tasks: Dict[str, Tuple[Any, str, str]]) -> None:
        """
        Update the tracking of high-priority tasks.

        Args:
            running_tasks: Current running tasks dictionary
        """
        self.last_running_tasks = {
            task_id: task_info
            for task_id, task_info in running_tasks.items()
            if self.is_high_priority(task_info[2])
        }

    def _pause_low_priority_tasks(self,
                                  running_tasks: Dict[str, Tuple[Any, str, str]],
                                  number_to_pause: int,
                                  pause_task: Callable) -> None:
        """
        Pause specified number of low-priority tasks.

        Args:
            running_tasks: Current running tasks dictionary
            number_to_pause: Number of low-priority tasks to pause
            pause_task: Callback function to pause tasks
        """
        # Find eligible low-priority tasks that are not already paused
        eligible_tasks = [
            task_id for task_id, task_info in running_tasks.items()
            if task_info[2] == "low" and task_id not in self.paused_tasks
        ]

        if not eligible_tasks:
            return

        # Randomly select tasks to pause
        tasks_to_pause = random.sample(
            eligible_tasks,
            min(number_to_pause, len(eligible_tasks))
        )

        for task_id in tasks_to_pause:
            self._pause_single_task(task_id, pause_task)
            self.paused_tasks.add(task_id)

    def _resume_low_priority_tasks(self,
                                   number_to_resume: int,
                                   resume_task: Callable) -> None:
        """
        Resume specified number of paused low-priority tasks.

        Args:
            number_to_resume: Number of tasks to resume
            resume_task: Callback function to resume tasks
        """
        if not self.paused_tasks:
            return

        # Randomly select tasks to resume
        tasks_to_resume = random.sample(
            list(self.paused_tasks),
            min(number_to_resume, len(self.paused_tasks))
        )

        for task_id in tasks_to_resume:
            self._resume_single_task(task_id, resume_task)
            self.paused_tasks.remove(task_id)

    def _pause_single_task(self, task_id: str, pause_task: Callable) -> None:
        """
        Pause a specific task by ID.

        Args:
            task_id: ID of the task to pause
            pause_task: Callback function to pause the task
        """
        try:
            if self.task_type == "io_liner_task":
                pause_task(task_id, "io_liner_task")
            elif self.task_type == "cpu_liner_task":
                pause_task(task_id, "cpu_liner_task")
        except:
            pass

    def _resume_single_task(self, task_id: str, resume_task: Callable) -> None:
        """
        Resume a specific task by ID.

        Args:
            task_id: ID of the task to resume
            resume_task: Callback function to resume the task
        """
        try:
            if self.task_type == "io_liner_task":
                resume_task(task_id, "io_liner_task")
            elif self.task_type == "cpu_liner_task":
                resume_task(task_id, "cpu_liner_task")
        except:
            pass

    def get_paused_task_count(self) -> int:
        """
        Get the number of currently paused tasks.

        Returns:
            int: Count of paused tasks
        """
        return len(self.paused_tasks)

    def clear_paused_tasks(self) -> None:
        """
        Clear all paused tasks from tracking.
        Useful for resetting state during shutdown.
        """
        self.paused_tasks.clear()
