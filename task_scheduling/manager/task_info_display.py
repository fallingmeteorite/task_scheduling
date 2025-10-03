# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import time

from task_scheduling.config import config
from task_scheduling.manager import task_status_manager


def format_tasks_info(tasks_dict) -> str:
    # Initialize counters
    tasks_queue_size = 0
    running_tasks_count = 0
    failed_tasks_count = 0

    # Traverse the tasks dictionary
    formatted_tasks = []
    for task_id, task_info in tasks_dict.items():
        # Calculate the number of running tasks and failed tasks
        if task_info['status'] == 'running':
            running_tasks_count += 1
        elif task_info['status'] == 'failed':
            failed_tasks_count += 1

        # Calculate the size of the tasks queue (assuming tasks in other states are in the queue)
        if task_info['status'] in ['waiting', 'queuing']:
            tasks_queue_size += 1

        # Format task information
        if task_info['start_time'] is None:
            elapsed_time = float('nan')
        elif task_info['end_time'] is None:
            elapsed_time = time.time() - task_info['start_time']
            if elapsed_time > config["watch_dog_time"]:
                elapsed_time = float('nan')
        else:
            elapsed_time = task_info['end_time'] - task_info['start_time']
            if elapsed_time > config["watch_dog_time"]:
                elapsed_time = float('nan')

        task_str = (f"name: {task_info['task_name']}, id: {task_id}, "
                    f"status: {task_info['status']}, elapsed time: {elapsed_time:.2f} seconds, task_type: {task_info['task_type']}")

        # If there is error information, add it
        if task_info['error_info'] is not None:
            task_str += f"\nerror_info: {task_info['error_info']}"

        formatted_tasks.append(task_str)

    # Output formatted task information
    output = (f"tasks queue size: {tasks_queue_size}, "
              f"running tasks count: {running_tasks_count}, "
              f"failed tasks count: {failed_tasks_count}\n") + "\n".join(formatted_tasks)

    return output


def get_tasks_info() -> str:
    return format_tasks_info(task_status_manager._task_status_dict)
