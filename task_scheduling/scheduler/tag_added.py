# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import asyncio
import multiprocessing
import sqlite3
import time
from typing import Callable

import psutil

from ..common import logger


class FunctionRunner:
    def __init__(self,
                 func: Callable,
                 task_name: str,
                 *args,
                 **kwargs) -> None:
        """
        Initialize the FunctionRunner with a function, task name, and arguments.

        Args:
            func (Callable): The function to execute.
            task_name (str): The name of the task.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.
        """
        self.func = func
        self.task_name = task_name
        self.args = args
        self.kwargs = kwargs
        self.process = None
        self.process_info = None
        self.cpu_usage_history = []
        self.memory_usage_history = []

    def run(self) -> None:
        """
        Start the function execution in a separate process and monitor its usage.
        """
        self.process = multiprocessing.Process(target=self._run_function)
        self.process.start()
        self.process_info = psutil.Process(self.process.pid)
        self._monitor_process()

    def _run_function(self) -> None:
        """
        Run the function. If the function is asynchronous, use asyncio to run it.
        """
        if asyncio.iscoroutinefunction(self.func):
            asyncio.run(self.func(*self.args, **self.kwargs))
        else:
            self.func(*self.args, **self.kwargs)

    def _monitor_process(self) -> None:
        """
        Monitor the CPU and memory usage of the running process.
        """
        try:
            while self.process.is_alive():
                # CPU usage
                cpu_usage = self.process_info.cpu_percent(interval=1)
                self.cpu_usage_history.append(cpu_usage)

                # Memory usage
                memory_usage = self.process_info.memory_info().rss / (1024 * 1024)
                self.memory_usage_history.append(memory_usage)

                logger.info(f"CPU Usage: {cpu_usage}%")
                logger.info(f"Memory Usage: {memory_usage:.2f} MB")

                time.sleep(1)
        except psutil.NoSuchProcess:
            pass
        finally:
            self.process.join()
            self._analyze_task_type()

    def _analyze_task_type(self) -> None:
        """
        Analyze the CPU and memory usage to determine the task type.
        """
        if not self.cpu_usage_history or not self.memory_usage_history:
            logger.info("No data to analyze.")
            return

        avg_cpu_usage = sum(self.cpu_usage_history) / len(self.cpu_usage_history)
        avg_memory_usage = sum(self.memory_usage_history) / len(self.memory_usage_history)

        logger.info(f"Average CPU Usage: {avg_cpu_usage}%")
        logger.info(f"Average Memory Usage: {avg_memory_usage:.2f} MB")

        # Heuristic to determine task type
        task_type = "CPU-intensive" if avg_cpu_usage > 50 else "I/O-intensive"
        self._save_to_db(task_type)




# Example usage
def example_cpu_intensive_function():
    """
    Example CPU-intensive function.
    """
    for i in range(1000000):
        _ = i * i


async def example_io_intensive_function():
    """
    Example I/O-intensive function.
    """
    for i in range(5):
        with open(f"temp_file_{i}.txt", "w") as f:
            f.write("Hello, World!" * 1000000)
        time.sleep(1)


if __name__ == "__main__":
    cpu_runner = FunctionRunner(example_cpu_intensive_function, "CPU_Task")
    cpu_runner.run()

    io_runner = FunctionRunner(example_io_intensive_function, "IO_Task")
    io_runner.run()
