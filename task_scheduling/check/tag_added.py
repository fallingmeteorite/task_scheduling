# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import asyncio
import multiprocessing
import time
import os
import threading
from typing import Callable

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
        self._start_time = None
        self._end_time = None

        # Monitoring data
        self._cpu_samples = []
        self._memory_samples = []
        self._disk_io_bytes = 0
        self._monitor_thread = None
        self._stop_monitoring = False

    def run(self) -> None:
        """Start task execution and monitoring"""
        self._process = multiprocessing.Process(
            target=self._run_function,
            name=f"TaskRunner-{self._task_name}"
        )
        self._process.start()
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

    def _get_process_cpu_usage(self) -> float:
        """Get process CPU usage (simplified version)"""
        try:
            # Use system calls to get process time
            if hasattr(os, 'times'):
                times = os.times()
                return times.user + times.system
            return 0.0
        except:
            return 0.0

    def _get_process_memory(self) -> int:
        """Get process memory usage (cross-platform simplified version)"""
        try:
            # For Linux/Unix systems
            if hasattr(os, 'getpid'):
                pid = os.getpid()
                try:
                    # Read /proc/pid/statm to get memory information
                    with open(f'/proc/{pid}/statm', 'r') as f:
                        memory_info = f.readline().split()
                    if len(memory_info) >= 2:
                        # Second item is resident set size, in pages
                        return int(memory_info[1]) * os.sysconf('SC_PAGESIZE')
                except:
                    pass

            # Fallback: use memory snapshot (not accurate but usable)
            import gc
            gc.collect()
            return 0  # Standard library cannot accurately get cross-process memory
        except:
            return 0

    def _monitor_process_simple(self) -> None:
        """Simplified process monitoring"""
        MONITOR_INTERVAL = 0.5
        last_cpu_time = self._get_process_cpu_usage()

        while self._process.is_alive() and not self._stop_monitoring:
            try:
                # Monitor start time
                monitor_start = time.monotonic()

                # Get CPU usage (based on time difference)
                current_cpu_time = self._get_process_cpu_usage()
                cpu_delta = current_cpu_time - last_cpu_time

                # Since we cannot accurately get cross-process CPU, we use execution time as reference
                elapsed = time.monotonic() - self._start_time
                if elapsed > 0:
                    # Estimate CPU usage (based on process alive time and actual time)
                    estimated_cpu = min(100.0, (cpu_delta / MONITOR_INTERVAL) * 100)
                    self._cpu_samples.append(estimated_cpu)

                last_cpu_time = current_cpu_time

                # Get memory usage
                memory_usage = self._get_process_memory()
                self._memory_samples.append(memory_usage)

                # Wait for next monitoring cycle
                elapsed_monitor = time.monotonic() - monitor_start
                sleep_time = MONITOR_INTERVAL - elapsed_monitor
                if sleep_time > 0:
                    time.sleep(sleep_time)

            except Exception as e:
                logger.warning(f"Monitoring error: {e}")
                break

    def _classify_task_simple(self) -> None:
        """Simplified task classification - only 'cpu' or 'io' types"""
        if not self._cpu_samples:
            logger.warning(f"No monitoring data collected for task: {self._task_name}")
            return

        total_duration = self._end_time - self._start_time
        if total_duration < 0.1:
            return

        # Calculate average CPU usage
        avg_cpu = sum(self._cpu_samples) / len(self._cpu_samples) if self._cpu_samples else 0

        # Only 'cpu' or 'io' types
        task_type = "cpu" if avg_cpu > 30 else "io"

        logger.info(
            f"Task Classification -> Name: {self._task_name} | "
            f"Type: {task_type} | "
            f"Avg CPU: {avg_cpu:.1f}% | "
            f"Duration: {total_duration:.2f}s"
        )

        task_function_type.append_to_dict(self._task_name, task_type)

    def _monitor_process(self) -> None:
        """Monitor process resource usage"""
        try:
            # Start monitoring thread
            self._stop_monitoring = False
            self._monitor_thread = threading.Thread(
                target=self._monitor_process_simple,
                name=f"Monitor-{self._task_name}"
            )
            self._monitor_thread.daemon = True
            self._monitor_thread.start()

            # Wait for process to finish
            self._process.join()
            self._stop_monitoring = True

            if self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=1.0)

        except Exception as e:
            logger.error(f"Monitor process error: {e}")
        finally:
            self._end_time = time.monotonic()
            self._classify_task_simple()

    def terminate(self) -> None:
        """Terminate process and monitoring"""
        self._stop_monitoring = True
        if self._process and self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=5.0)
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)
