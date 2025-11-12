# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Command-line interface for task scheduler system.

This module provides a command-line interface for creating and managing
tasks through the task scheduler system with web UI integration.
"""

import os
import shlex
import sys

from .task_creation import task_creation
from .manager import task_scheduler
from .webui import start_task_status_ui
from .common import logger
from .variable import *


def command_creation(task_name: str, command: str) -> str:
    """Create a task that executes a shell command.

    Args:
        task_name: Name identifier for the task.
        command: Shell command to execute.

    Returns:
        str: Task ID of the created task.
    """

    def wrapper(command):
        """Wrapper function to execute shell command."""
        os.system(command)

    return task_creation(
        delay=None,
        daily_time=None,
        function_type=FUNCTION_TYPE_IO,
        timeout_processing=False,
        async_function=False,
        task_name=task_name,
        func=wrapper,
        priority=priority_high,
        command=command
    )


def parse_input(user_input: str) -> dict:
    """Parse user input string into command arguments.

    Args:
        user_input: Raw input string from user.

    Returns:
        dict: Parsed arguments with keys 'command' and 'name'.
    """
    parts = shlex.split(user_input)
    args = {'command': None, 'name': 'command_task'}
    arg_map = {'-cmd': 'command', '-n': 'name', '-name': 'name'}

    it = iter(parts)
    for arg in it:
        if arg in arg_map:
            args[arg_map[arg]] = next(it, None)

    return args


def main():
    """Main entry point for the command-line task scheduler."""
    logger.info("The task scheduler starts.")
    start_task_status_ui()

    while True:
        try:
            logger.info("Wait for the task to be added.")
            input_info = input().strip()

            if not input_info:
                continue

            args = parse_input(input_info)
            logger.info(f"Parameter: {args}")

            if not args['command'] or not args['name']:
                logger.warning("The -cmd or -n parameter must be provided")
                continue

            task_id = command_creation(command=args['command'], task_name=args['name'])
            logger.info(f"Create a success. task ID: {task_id}")

        except KeyboardInterrupt:
            logger.info("Starting shutdown TaskScheduler.")
            task_scheduler.shutdown_scheduler()
            sys.exit(0)
        except Exception as e:
            logger.error(e)


if __name__ == "__main__":
    main()
