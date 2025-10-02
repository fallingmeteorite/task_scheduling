import os
import shlex
import sys

from .task_creation import task_creation, shutdown
from task_scheduling.task_info import start_task_status_ui
from .common.log_config import logger
from task_scheduling import *


def command_creation(task_name: str,
                     command: str) -> str or None:
    def wrapper(command) -> None:
        os.system(command)

    return task_creation(None, None, scheduler_io, False, task_name, wrapper, priority_high, command)

def parse_input(user_input):
    """Simplified input parsing"""
    parts = shlex.split(user_input)
    args = {'command': None, 'name': 'command_task'}

    i = 0
    while i < len(parts):
        arg = parts[i]

        if arg in ['-cmd']:
            args['command'] = parts[i + 1]
            i += 1
        elif arg in ['-n', '-name']:
            args['name'] = parts[i + 1]
            i += 1

        i += 1

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

            # Parse the input
            args = parse_input(input_info)
            logger.info(f"Parameter: {args}")

            if not args['command'] or not args['name']:
                logger.warning("The -cmd or -n parameter must be provided")
                continue

            # Create a task
            task_id = command_creation(
                command=args['command'],
                task_name=args['name']
            )

            logger.info(f"Create a success. task ID: {task_id}")

        except KeyboardInterrupt:
            logger.info("Starting shutdown TaskScheduler.")
            shutdown(True)
            sys.exit(0)
        except Exception as e:
            logger.error(e)


if __name__ == "__main__":
    main()
