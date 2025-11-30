## 功能说明

字典中的任务名字将会以`task_group_name|task_name`显示,当名字任务为`task_group_name`被结束,所有的以`task_group_name|task_name`显示的任务都会一并结束,`task_group_name`是这个任务树中的主任务(该任务实际只是一个载体,没有功能)

## 参数说明

**task_group_name**: 这个任务树中的主任务名字(该任务实际只是一个载体,没有功能),所有的分支任务都会加上该主任务的名字

**task_dict**: `键`存储任务名字,`值`存储要执行的函数,是否启用超时检测强制终止 (`True`, `False`) 和函数需要的参数 (必须按照顺序)

## 使用示例:

```python
import time


def liner_task(input_info):
    while True:
        time.sleep(1)
        print(input_info)


if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation
    from task_scheduling.manager import task_scheduler
    from task_scheduling.quick_creation import task_group
    from task_scheduling.server_webui import start_task_status_ui
    from task_scheduling.variable import *

    start_task_status_ui()

    task_group_name = "main_task"

    task_dict = {
        "task1": (liner_task, True, 1111),
        "task2": (liner_task, True, 2222),
        "task3": (liner_task, True, 3333),
    }

    task_id1 = task_creation(
        None, None, FUNCTION_TYPE_CPU, True, task_group_name,
        task_group, priority_low, task_dict)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler()