# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import asyncio
import multiprocessing
import time
from typing import Callable

import psutil

from ..common import logger
from ..function_data import task_function_type
from ..utils import is_async_function


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

        # Data containers for monitoring
        self._cpu_usage_history = []  # CPU usage percentage per second
        self._disk_io_history = []  # Disk IO bytes per second
        self._net_io_history = []  # Network IO bytes per second

    def run(self) -> None:
        self._process = multiprocessing.Process(target=self._run_function)
        self._process.start()
        self._process_info = psutil.Process(self._process.pid)
        self._start_time = time.time()
        self._monitor_process()

    def _run_function(self) -> None:
        # Determine if function is async and run accordingly
        if is_async_function(self._func):
            asyncio.run(self._func(*self._args, **self._kwargs))
        else:
            self._func(*self._args, **self._kwargs)

    def _monitor_process(self) -> None:
        try:
            last_disk_io = self._process_info.io_counters()
            last_net_io = psutil.net_io_counters()

            while self._process.is_alive():
                # Monitor CPU usage
                cpu_usage = self._process_info.cpu_percent(interval=1)
                self._cpu_usage_history.append(cpu_usage)

                # Calculate disk IO increment
                current_disk_io = self._process_info.io_counters()
                disk_io_bytes = (current_disk_io.read_bytes - last_disk_io.read_bytes) + \
                                (current_disk_io.write_bytes - last_disk_io.write_bytes)
                self._disk_io_history.append(disk_io_bytes)
                last_disk_io = current_disk_io

                # Calculate network IO increment
                current_net_io = psutil.net_io_counters()
                net_io_bytes = (current_net_io.bytes_sent - last_net_io.bytes_sent) + \
                               (current_net_io.bytes_recv - last_net_io.bytes_recv)
                self._net_io_history.append(net_io_bytes)
                last_net_io = current_net_io

                # Log detailed monitoring information
                logger.debug(f"CPU: {cpu_usage}% | DiskIO: {disk_io_bytes} bytes | NetIO: {net_io_bytes} bytes")

        except psutil.NoSuchProcess:
            pass
        finally:
            self._end_time = time.time()
            self._process.join()
            self._analyze_task_type()

    def _analyze_task_type(self) -> None:
        """Analyze resource usage to classify task type"""
        if not self._cpu_usage_history:
            return

        total_duration = self._end_time - self._start_time

        # Calculate CPU time integral (units: percentage·seconds)
        cpu_time_integral = sum(self._cpu_usage_history)  # Sampled every second

        # Calculate IO time integral (units: MB·seconds)
        io_time_integral = sum(
            (disk + net) / (1024 * 1024)  # Convert to MB
            for disk, net in zip(self._disk_io_history, self._net_io_history)
        )

        # Set resource density thresholds (based on experience)
        CPU_DENSITY_THRESHOLD = 30 * total_duration  # 30% CPU usage for the total duration
        IO_DENSITY_THRESHOLD = 10 * total_duration  # 10MB/s IO for the total duration

        # Classification logic
        is_cpu_dominant = cpu_time_integral > CPU_DENSITY_THRESHOLD
        is_io_dominant = io_time_integral > IO_DENSITY_THRESHOLD

        if is_cpu_dominant and is_io_dominant:
            # Mixed type task, classified by the dominant feature
            task_type = "CPU-intensive" if (cpu_time_integral / CPU_DENSITY_THRESHOLD) > \
                                           (io_time_integral / IO_DENSITY_THRESHOLD) \
                else "I/O-intensive"
        elif is_cpu_dominant:
            task_type = "CPU-intensive"
        elif is_io_dominant:
            task_type = "I/O-intensive"
        else:
            # Low resource type task, classified by the maximum relative value
            cpu_ratio = cpu_time_integral / CPU_DENSITY_THRESHOLD
            io_ratio = io_time_integral / IO_DENSITY_THRESHOLD
            task_type = "CPU-intensive" if cpu_ratio > io_ratio else "I/O-intensive"

        # Log task classification result
        logger.info(
            f"Task Classification Result:\n"
            f"Name: {self._task_name}\n"
            f"Type: {task_type}"
        )

        # Store task type in dictionary
        task_function_type.append_to_dict(self._task_name, task_type)
