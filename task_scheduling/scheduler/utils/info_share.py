# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Shared status information management for multiprocessing.

This module provides a thread-safe way to share task status and signal information
across multiple processes using multiprocessing.Manager.
"""
import multiprocessing

from multiprocessing import Manager


class SharedStatusInfo:
    """
    A class for managing shared task information across multiple processes.
    This enables inter-process communication for task status and signals.
    """

    def __init__(self) -> None:
        # Initialize attributes as None, will be lazily initialized when accessed
        self._manager = None
        self._channel = True
        self._task_pid = None
        self._task_status_queue = None
        self._task_signal_transmission = None

    def _initialize(self) -> None:
        """Lazy initialization, create Manager only in the main process"""
        if self._manager is None and multiprocessing.current_process().name == 'MainProcess':
            self._manager = Manager()
            self._task_pid = self._manager.dict()
            self._task_status_queue = self._manager.Queue()
            self._task_signal_transmission = self._manager.dict()

    @property
    def task_pid(self) -> str:
        """Return the task pid"""
        self._initialize()
        return self._task_pid

    @property
    def task_status_queue(self) -> None:
        """Get the task status queue with lazy initialization"""
        self._initialize()
        return self._task_status_queue

    @property
    def task_signal_transmission(self) -> None:
        """Get the task signal transmission dictionary with lazy initialization"""
        self._initialize()
        return self._task_signal_transmission

    @property
    def manager(self) -> None:
        """Get the manager instance with lazy initialization"""
        self._initialize()
        return self._manager

    def channel_shutdown(self) -> None:
        """Reset all variables"""
        self._manager = None
        self._channel = True
        self._task_pid = None
        self._task_status_queue = None
        self._task_signal_transmission = None
