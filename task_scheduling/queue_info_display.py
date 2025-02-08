import time

from .config import config
from .manager import task_status_manager


def format_tasks_info(tasks_dict):
    # 初始化计数器
    tasks_queue_size = 0
    running_tasks_count = 0
    failed_tasks_count = 0

    # 遍历任务字典
    formatted_tasks = []
    for task_id, task_info in tasks_dict.items():
        # 计算正在运行的任务数和失败的任务数
        if task_info['status'] == 'running':
            running_tasks_count += 1
        elif task_info['status'] == 'failed':
            failed_tasks_count += 1

        # 计算任务队列的大小（假设其他状态的任务都在队列中）
        if task_info['status'] in ['waiting', 'queuing']:
            tasks_queue_size += 1

        # 格式化任务信息
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
                    f"status: {task_info['status']}, elapsed Time: {elapsed_time:.2f} seconds")

        # 如果有错误信息，则添加错误信息
        if task_info['error_info'] is not None:
            task_str += f"\nerror_info: {task_info['error_info']}"

        formatted_tasks.append(task_str)

    # 输出格式化后的任务信息
    output = (f"tasks queue size: {tasks_queue_size}, "
              f"running tasks count: {running_tasks_count}, "
              f"failed tasks count: {failed_tasks_count}\n") + "\n".join(formatted_tasks)

    return output


def get_tasks_info():
    return format_tasks_info(task_status_manager.task_status_dict)
