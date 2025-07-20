# -*- coding: utf-8 -*-
import asyncio
import multiprocessing
import time
from typing import Callable, Tuple, Dict

import psutil
from ..common import logger
from .function_type import TaskFunctionType
from ..utils import is_async_function

task_function_type = TaskFunctionType


class FunctionRunner:
    def __init__(self, func: Callable, task_name: str, *args, **kwargs) -> None:
        self._func = func
        self._task_name = task_name
        self._args = args
        self._kwargs = kwargs
        self._process = None
        self._process_info = None
        self._start_time = None
        self._end_time = None

        # Use more efficient data structures for monitoring
        self._cpu_usage = 0.0
        self._disk_io_bytes = 0
        self._net_io_bytes = 0
        self._samples = 0

    def run(self) -> None:
        """Start task execution and monitoring"""
        self._process = multiprocessing.Process(
            target=self._run_function,
            name=f"TaskRunner-{self._task_name}"
        )
        self._process.start()
        self._process_info = psutil.Process(self._process.pid)
        self._start_time = time.monotonic()
        self._monitor_process()

    def _run_function(self) -> None:
        """Execute the target function"""
        try:
            if is_async_function(self._func):
                asyncio.run(self._func(*self._args, **self._kwargs))
            else:
                self._func(*self._args, **self._kwargs)
        except Exception as e:
            logger.error(f"Task {self._task_name} failed: {str(e)}")

    def _monitor_process(self) -> None:
        """Monitor process resource usage"""
        try:
            # Get initial IO counters
            last_disk_io = self._process_info.io_counters()
            last_net_io = psutil.net_io_counters()

            # Set monitoring interval (seconds)
            MONITOR_INTERVAL = 0.5

            while self._process.is_alive():
                start_monitor = time.monotonic()

                # Get CPU usage (blocking for interval seconds)
                cpu_usage = self._process_info.cpu_percent(interval=MONITOR_INTERVAL)
                self._cpu_usage += cpu_usage

                # Calculate disk and network IO increments
                current_disk_io = self._process_info.io_counters()
                current_net_io = psutil.net_io_counters()

                disk_io = (current_disk_io.read_bytes - last_disk_io.read_bytes) + \
                          (current_disk_io.write_bytes - last_disk_io.write_bytes)
                net_io = (current_net_io.bytes_sent - last_net_io.bytes_sent) + \
                         (current_net_io.bytes_recv - last_net_io.bytes_recv)

                self._disk_io_bytes += disk_io
                self._net_io_bytes += net_io
                self._samples += 1

                last_disk_io = current_disk_io
                last_net_io = current_net_io

                # Dynamically adjust monitoring interval to avoid overhead
                elapsed = time.monotonic() - start_monitor
                if elapsed < MONITOR_INTERVAL:
                    time.sleep(MONITOR_INTERVAL - elapsed)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        finally:
            self._end_time = time.monotonic()
            if self._process.is_alive():
                self._process.terminate()
                self._process.join()
            self._classify_task()

    def _classify_task(self) -> None:
        """Classify task type based on resource usage"""
        if self._samples == 0:
            logger.warning(f"No monitoring data collected for task: {self._task_name}")
            return

        total_duration = self._end_time - self._start_time
        if total_duration < 0.1:  # Ignore very short tasks
            return

        # Calculate average CPU usage (% of total CPU)
        avg_cpu_usage = self._cpu_usage / self._samples

        # Calculate total IO (MB)
        total_io_mb = (self._disk_io_bytes + self._net_io_bytes) / (1024 * 1024)

        # Calculate IO rate (MB/s)
        io_rate = total_io_mb / total_duration if total_duration > 0 else 0

        # Classification thresholds (adjustable based on needs)
        CPU_INTENSIVE_THRESHOLD = 50  # Average CPU usage > 50%
        IO_INTENSIVE_THRESHOLD = 5  # IO rate > 5MB/s

        # Classification logic
        is_cpu_intensive = avg_cpu_usage > CPU_INTENSIVE_THRESHOLD
        is_io_intensive = io_rate > IO_INTENSIVE_THRESHOLD

        if is_cpu_intensive and is_io_intensive:
            # Mixed-type task, classify by dominant factor
            cpu_ratio = avg_cpu_usage / CPU_INTENSIVE_THRESHOLD
            io_ratio = io_rate / IO_INTENSIVE_THRESHOLD
            task_type = "CPU-intensive" if cpu_ratio > io_ratio else "I/O-intensive"
        elif is_cpu_intensive:
            task_type = "CPU-intensive"
        elif is_io_intensive:
            task_type = "I/O-intensive"
        else:
            # Lightweight task, classify by relative ratio
            task_type = "CPU-light" if avg_cpu_usage > io_rate else "I/O-light"

        logger.info(
            f"Task Classification -> Name: {self._task_name} | "
            f"Type: {task_type} | "
            f"Avg CPU: {avg_cpu_usage:.1f}% | "
            f"IO Rate: {io_rate:.2f}MB/s | "
            f"Duration: {total_duration:.2f}s"
        )

        # Store task type
        task_function_type.append_to_dict(self._task_name, task_type)
