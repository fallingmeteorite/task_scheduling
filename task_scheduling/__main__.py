# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import os
import shlex
import sys

from .task_creation import task_creation
from .manager import task_scheduler
from .webui import start_task_status_ui
from .common import logger
from .variable import *


def command_creation(task_name: str, command: str) -> str:
    def wrapper(command):
        os.system(command)

    return task_creation(None, None, FUNCTION_TYPE_IO, False, task_name, wrapper, priority_high, command)


def parse_input(user_input):
    parts = shlex.split(user_input)
    args = {'command': None, 'name': 'command_task'}
    arg_map = {'-cmd': 'command', '-n': 'name', '-name': 'name'}

    it = iter(parts)
    for arg in it:
        if arg in arg_map:
            args[arg_map[arg]] = next(it, None)

    return args


def main():
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
