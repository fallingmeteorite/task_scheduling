# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Task dependency management module.

This module provides functionality for managing task dependencies
and triggering dependent tasks based on main task completion status.
"""

import asyncio
import threading
from typing import Callable

from task_scheduling.client import submit_task
from task_scheduling.common import logger
from task_scheduling.manager import task_status_manager
from task_scheduling.result_server import get_task_result
from task_scheduling.scheduler import get_result_api
from task_scheduling.task_creation import task_creation


async def _wait_main_task_result_local(condition: str, main_task_id: str,
                                       dependent_task: Callable, args) -> None:
    """
    Wait for the main task to complete and then trigger the dependent task.

    Args:
        condition: Condition under which the main task is considered executed
        main_task_id: ID of the main task
        dependent_task: The dependent task function to execute
        args: Arguments for the dependent task
    """
    task_type = task_status_manager.get_task_type(main_task_id)
    while True:
        await asyncio.sleep(1.0)
        result = get_result_api(task_type, main_task_id)

        # When the task status meets the trigger conditions
        if result == condition:
            task_creation(args[0], args[1], args[2], args[3], args[4], dependent_task, *args[5:])
            break

        # If completed, there will be a return result
        if condition == "completed action":
            if result is not None and result not in ["timeout action", "cancelled action", "failed action",
                                                     "completed action"]:
                if not isinstance(result, tuple):
                    logger.error("The return value is not a tuple!")
                    break
                args += result
                task_creation(args[0], args[1], args[2], args[3], args[4], dependent_task, *args[5:])
                break

        # If completed, no result is returned
        if result == "completed action":
            if result == condition:
                task_creation(args[0], args[1], args[2], args[3], args[4], dependent_task, *args[5:])
                break


async def _wait_main_task_result_network(condition: str, main_task_id: str,
                                         dependent_task: Callable, args) -> None:
    """
    Wait for the main task to complete and then trigger the dependent task.

    Args:
        condition: Condition under which the main task is considered executed
        main_task_id: ID of the main task
        dependent_task: The dependent task function to execute
        args: Arguments for the dependent task
    """
    while True:
        await asyncio.sleep(1.0)
        result = await get_task_result(main_task_id)

        # When the task status meets the trigger conditions
        if result == condition:
            submit_task(args[0], args[1], args[2], args[3], args[4], dependent_task, *args[5:])
            break

        # If completed, there will be a return result
        if condition == "completed action":
            if result is not None and result not in ["timeout action", "cancelled action", "failed action",
                                                     "completed action"]:
                if not isinstance(result, tuple):
                    logger.error("The return value is not a tuple!")
                    break
                args += result
                submit_task(args[0], args[1], args[2], args[3], args[4], dependent_task, *args[5:])
                break

        # If completed, no result is returned
        if result == "completed action":
            if result == condition:
                submit_task(args[0], args[1], args[2], args[3], args[4], dependent_task, *args[5:])
                break


class TaskDependencyLocal:
    """
    Task dependency local, handles task dependencies using an asynchronous event loop
    """

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self._start_event_loop()

    def _start_event_loop(self):
        """Start the event loop"""

        def run_loop():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()

        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()

    def _run_in_async_loop(self, coro):
        """Run a coroutine in an asynchronous loop"""
        asyncio.run_coroutine_threadsafe(coro, self.loop)

    def after_completion(self, main_task_id: str, dependent_task: Callable, *args) -> None:
        """
        Trigger a dependent task to run after the main task completes.

        Args:
            main_task_id: ID of the main task
            dependent_task: The dependent task function to execute
            *args: Arguments for the dependent task
        """
        self._run_in_async_loop(
            _wait_main_task_result_local("completed action", main_task_id, dependent_task, args)
        )

    def after_cancel(self, main_task_id: str, dependent_task: Callable, *args) -> None:
        """
        Trigger a dependent task to run after the main task is cancelled.

        Args:
            main_task_id: ID of the main task
            dependent_task: The dependent task function to execute
            *args: Arguments for the dependent task
        """
        self._run_in_async_loop(
            _wait_main_task_result_local("cancelled action", main_task_id, dependent_task, args)
        )

    def after_timeout(self, main_task_id: str, dependent_task: Callable, *args) -> None:
        """
        Trigger a dependent task to run after the main task times out.

        Args:
            main_task_id: ID of the main task
            dependent_task: The dependent task function to execute
            *args: Arguments for the dependent task
        """
        self._run_in_async_loop(
            _wait_main_task_result_local("timeout action", main_task_id, dependent_task, args)
        )

    def after_error(self, main_task_id: str, dependent_task: Callable, *args) -> None:
        """
        Trigger a dependent task to run after the main task fails with error.

        Args:
            main_task_id: ID of the main task
            dependent_task: The dependent task function to execute
            *args: Arguments for the dependent task
        """
        self._run_in_async_loop(
            _wait_main_task_result_local("failed action", main_task_id, dependent_task, args)
        )


class TaskDependencyNetwork:
    """
    Task dependency network, handles task dependencies using an asynchronous event loop
    """

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self._start_event_loop()

    def _start_event_loop(self):
        """Start the event loop"""

        def run_loop():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()

        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()

    def _run_in_async_loop(self, coro):
        """Run a coroutine in an asynchronous loop"""
        asyncio.run_coroutine_threadsafe(coro, self.loop)

    def after_completion(self, main_task_id: str, dependent_task: Callable, *args) -> None:
        """
        Trigger a dependent task to run after the main task completes.

        Args:
            main_task_id: ID of the main task
            dependent_task: The dependent task function to execute
            *args: Arguments for the dependent task
        """
        self._run_in_async_loop(
            _wait_main_task_result_network("completed action", main_task_id, dependent_task, args)
        )

    def after_cancel(self, main_task_id: str, dependent_task: Callable, *args) -> None:
        """
        Trigger a dependent task to run after the main task is cancelled.

        Args:
            main_task_id: ID of the main task
            dependent_task: The dependent task function to execute
            *args: Arguments for the dependent task
        """
        self._run_in_async_loop(
            _wait_main_task_result_network("cancelled action", main_task_id, dependent_task, args)
        )

    def after_timeout(self, main_task_id: str, dependent_task: Callable, *args) -> None:
        """
        Trigger a dependent task to run after the main task times out.

        Args:
            main_task_id: ID of the main task
            dependent_task: The dependent task function to execute
            *args: Arguments for the dependent task
        """
        self._run_in_async_loop(
            _wait_main_task_result_network("timeout action", main_task_id, dependent_task, args)
        )

    def after_error(self, main_task_id: str, dependent_task: Callable, *args) -> None:
        """
        Trigger a dependent task to run after the main task fails with error.

        Args:
            main_task_id: ID of the main task
            dependent_task: The dependent task function to execute
            *args: Arguments for the dependent task
        """
        self._run_in_async_loop(
            _wait_main_task_result_network("failed action", main_task_id, dependent_task, args)
        )


# Global task dependency manager instance
task_dependency_local = TaskDependencyLocal()

# Global task dependency manager instance
task_dependency_network = TaskDependencyNetwork()
