# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import random


class TaskCounter:
    def __init__(self, task_type: str = None):
        """Initialize task counter with tracking capabilities

        Args:
            task_type: Type of task ('io_liner_task' or 'cpu_liner_task')
        """
        self.last_running_tasks = {}  # Tracks previous running tasks {task_id: [future, task_name, priority]}
        self.target_priority = "high"  # Priority level to monitor for preemption
        self.task_type = task_type  # Task type identifier
        self.paused_tasks = set()  # Set of currently paused task IDs
        self.count = 0  # Limit the quantity

    def add(self, max_count) -> None:
        if self.count >= max_count:
            return False
        self.count += 1
        return True


    def is_high_priority(self, priority: str) -> bool:
        """Check if a task has the target priority level

        Args:
            priority: Priority string to check

        Returns:
            bool: True if matches target priority
        """
        return priority == self.target_priority

    def schedule_tasks(self, running_tasks):
        """Main scheduling function that manages task preemption

        1. Monitors current running tasks
        2. Pauses low-priority tasks when high-priority tasks appear
        3. Resumes low-priority tasks when high-priority tasks complete

        Args:
            running_tasks: Dictionary of currently running tasks
        """
        # Count current high-priority tasks
        current_high_count = sum(
            1 for task_info in running_tasks.values()
            if self.is_high_priority(task_info[2])
        )

        # Compare with previous count
        previous_high_count = len(self.last_running_tasks)
        delta = current_high_count - previous_high_count

        if delta > 0:
            self._pause_low_priority(running_tasks, delta)
        elif delta < 0:
            self.count = self.count - delta
            self._resume_low_priority(abs(delta))

        # Update tracking of high-priority tasks
        self.last_running_tasks = {
            task_id: info
            for task_id, info in running_tasks.items()
            if self.is_high_priority(info[2])
        }

    def _pause_low_priority(self, running_tasks, number_to_pause):
        """Pause specified number of low-priority tasks

        Args:
            running_tasks: Current running tasks dictionary
            number_to_pause: Number of tasks to pause
        """
        eligible_tasks = [
            task_id for task_id, info in running_tasks.items()
            if info[2] == "low" and task_id not in self.paused_tasks
        ]

        for task_id in random.sample(eligible_tasks, min(number_to_pause, len(eligible_tasks))):
            self.pause_task(task_id)
            self.paused_tasks.add(task_id)

    def _resume_low_priority(self, number_to_resume):
        """Resume specified number of paused low-priority tasks

        Args:
            number_to_resume: Number of tasks to resume
        """
        for task_id in random.sample(self.paused_tasks, min(number_to_resume, len(self.paused_tasks))):
            self.resume_task(task_id)
            self.paused_tasks.remove(task_id)

    def pause_task(self, task_id: str) -> None:
        """Pause a specific task by ID

        Args:
            task_id: ID of task to pause
        """
        from ..scheduler import cpu_liner_task, io_liner_task

        if self.task_type == "io_liner_task":
            io_liner_task.pause_and_resume_task(task_id, "pause")
        else:
            cpu_liner_task.pause_and_resume_task(task_id, "pause")

    def resume_task(self, task_id: str) -> None:
        """Resume a specific task by ID

        Args:
            task_id: ID of task to resume
        """
        from ..scheduler import cpu_liner_task, io_liner_task

        if self.task_type == "io_liner_task":
            io_liner_task.pause_and_resume_task(task_id, "resume")
        else:
            cpu_liner_task.pause_and_resume_task(task_id, "resume")
