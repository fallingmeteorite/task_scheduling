# -*- coding: utf-8 -*-
# Author: fallingmeteorite

import queue
import sys
import threading
import time
from typing import Callable, Optional, Any


# Context Manager class
class _MonitorContextManager:
    def __init__(self, condition_func: Callable, error_message: str) -> None:
        self._condition_func = condition_func
        self._error_message = error_message
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def __enter__(self) -> Any:
        # Start the monitoring thread
        self._monitor_thread = threading.Thread(target=self._monitor, daemon=True)  # Set as daemon thread
        self._monitor_thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        # Stop monitoring threads
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1)  # Wait for the thread to end

    def _monitor(self) -> None:
        while not self._stop_event.is_set():
            if self._condition_func():
                sys.exit(0)
            time.sleep(1)  # Check every 1 second


# 2: Timeout Trigger
def _check_timeout(start_time: float, timeout: int) -> bool:
    """
    If the difference between the current time and start_time exceeds the timeout, the condition is triggered.
    """
    return time.time() - start_time > timeout


# 1: Read instructions from the process pipeline
def _check_instruction_from_queue(shared_queue: queue.Queue, task_id: str) -> bool:
    """
    Monitor for specific instructions in the shared queue.
    """
    if not shared_queue.empty():
        instruction = shared_queue.get(timeout=1)  # Non-blocking fetch instructions
        if isinstance(instruction, str):
            if instruction == task_id:
                return True
        shared_queue.put(instruction)
    return False
