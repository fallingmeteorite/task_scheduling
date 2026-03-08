# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Time bucket queue implementation for efficient task scheduling.

This module provides a thread-safe time bucket queue that groups tasks with the
same execution time into buckets, reducing the number of items in the priority
queue and enabling batch processing of tasks scheduled for the same time.
"""
import threading
import heapq
from typing import Dict, List, Tuple, Optional


class TimeBucketQueue:
    """
    Time bucket queue: Groups tasks with the same execution time into buckets.
    This optimization reduces the number of items in the priority queue and
    enables batch processing of tasks scheduled for the same time.
    """

    def __init__(self):
        # Min-heap that only stores execution timestamps
        self._time_heap = []

        # Time buckets: {execution_time: [tasks]}
        self._buckets: Dict[float, List[Tuple]] = {}

        # Lock for thread safety
        self._lock = threading.RLock()

    def put(self, execution_time: float, task: Tuple) -> None:
        """
        Add a task to the appropriate time bucket.

        Args:
            execution_time: The timestamp when the task should execute
            task: The task tuple to be stored
        """
        with self._lock:
            # If this timestamp doesn't have a bucket yet, create one
            if execution_time not in self._buckets:
                self._buckets[execution_time] = []
                heapq.heappush(self._time_heap, execution_time)

            # Add the task to the bucket
            self._buckets[execution_time].append(task)

    def get_ready_buckets(self, current_time: float) -> List[Tuple[float, List[Tuple]]]:
        """
        Get all buckets whose execution time has arrived.

        Args:
            current_time: The current timestamp

        Returns:
            List of tuples (execution_time, list_of_tasks) for all expired buckets
        """
        ready_buckets = []

        with self._lock:
            # Check if the earliest timestamp has arrived
            while self._time_heap and self._time_heap[0] <= current_time:
                execution_time = heapq.heappop(self._time_heap)

                # Get all tasks for this timestamp
                tasks = self._buckets.pop(execution_time, [])

                if tasks:  # Only add non-empty buckets
                    ready_buckets.append((execution_time, tasks))

        return ready_buckets

    def peek_next_time(self) -> Optional[float]:
        """
        Get the next execution time without removing it.

        Returns:
            The next execution timestamp or None if queue is empty
        """
        with self._lock:
            return self._time_heap[0] if self._time_heap else None

    def empty(self) -> bool:
        """
        Check if the queue is empty.

        Returns:
            True if no tasks are pending, False otherwise
        """
        with self._lock:
            return len(self._time_heap) == 0

    def _total_size(self) -> int:
        """
        Get the total number of tasks across all buckets.

        Returns:
            Total task count
        """
        with self._lock:
            return sum(len(tasks) for tasks in self._buckets.values())

    def clear(self) -> None:
        """
        Clear all tasks from the queue.
        """
        with self._lock:
            self._time_heap.clear()
            self._buckets.clear()
