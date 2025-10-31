# -*- coding: utf-8 -*-
# Author: fallingmeteorite
from multiprocessing import Manager

class SharedTaskInfo:
    """
    A class for managing shared task information across multiple processes.
    This enables inter-process communication for task status and signals.
    """

    def __init__(self):
        # Initialize a multiprocessing manager to handle shared objects
        self.manager = Manager()

        # Queue for task status updates - allows processes to send status messages
        self.task_status_queue = self.manager.Queue()

        # Dictionary for task signal transmission - enables key-value sharing between processes
        self.task_signal_transmission = self.manager.dict()


# Create a global instance of SharedTaskInfo for use across the application
shared_task_info = SharedTaskInfo()
