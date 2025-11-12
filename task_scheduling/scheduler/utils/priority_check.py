# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Task counter with priority-based scheduling capabilities.

This module provides a thread-safe task counter that manages task preemption
based on priority levels, allowing high-priority tasks to temporarily pause
low-priority tasks when resources are constrained.
"""
import threading

from typing import Dict, Set, Tuple, Any, Optional


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
        self._lock = threading.Lock()  # Thread lock for thread-safe operations

    def add_count(self, max_count: int) -> bool:
        """
        Increment task count if within maximum limit.

        Args:
            max_count: Maximum allowed task count

        Returns:
            True if count was successfully added, False if limit reached
        """
        with self._lock:
            if self.count >= max_count:
                return False

            self.count += 1
            return True

    def is_high_priority(self, priority: str) -> bool:
        """
        Check if a task has the target high priority level.

        Args:
            priority: Priority string to check

        Returns:
            True if priority matches target priority
        """
        return priority == self.target_priority
