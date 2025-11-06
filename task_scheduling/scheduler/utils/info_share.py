# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import multiprocessing
from multiprocessing import Manager


class SharedTaskInfo:
    """
    A class for managing shared task information across multiple processes.
    This enables inter-process communication for task status and signals.
    """

    def __init__(self):
        # Initialize attributes as None, will be lazily initialized when accessed
        self._manager = None
        self._task_status_queue = None
        self._task_signal_transmission = None

    def _initialize(self):
        """Lazy initialization, create Manager only in the main process"""
        if self._manager is None and multiprocessing.current_process().name == 'MainProcess':
            self._manager = Manager()
            self._task_status_queue = self._manager.Queue()
            self._task_signal_transmission = self._manager.dict()

    @property
    def task_status_queue(self):
        """Get the task status queue with lazy initialization"""
        self._initialize()
        return self._task_status_queue

    @property
    def task_signal_transmission(self):
        """Get the task signal transmission dictionary with lazy initialization"""
        self._initialize()
        return self._task_signal_transmission

    @property
    def manager(self):
        """Get the manager instance with lazy initialization"""
        self._initialize()
        return self._manager


# Create a global instance of SharedTaskInfo for use across the application
shared_task_info = SharedTaskInfo()