## 任务优先级调度

task_creation(delay: int or None, daily_time: str or None, function_type: str, timeout_processing: bool, task_name:
str, func: Callable, *args, **kwargs) -> str or None

- 警告:

只有CPU线性任务和IO线性任务,才存在优先级调度

- 功能说明:

在低优先级的任务填满调度器时,需要马上运行一个任务可以将优先等级设置为高,该任务将随机暂停一个低优先级的任务,然后运行自身,保证总正在运行的任务
不超过调度器设置上线,但是暂停的任务依然暂用资源和内存,只是不会占用CPU资源,当高优先等级任务结束后会自动恢复暂停最先暂停的低优先等级任务,如果
调度器没有占用满,则不会暂停低有限等级任务

- 参数说明:

**priority**: 任务优先级 (`priority_low`, `priority_high`)

- 使用示例:

```python
import time
from task_scheduling.variable import *
from task_scheduling.utils import interruptible_sleep


def linear_task(input_info):
    for i in range(10):
        interruptible_sleep(1)
        print(f"Linear task: {input_info} - {i}")


if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation
    from task_scheduling.manager import task_scheduler
    from task_scheduling.server_webui import start_task_status_ui

    start_task_status_ui()

    task_id1 = task_creation(
        None, None, FUNCTION_TYPE_IO, True, "linear_task",
        linear_task, priority_high, "Hello Linear"
    )

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler()
```

```python
def linear_task(input_info):
    import time
    from task_scheduling.utils import interruptible_sleep
    for i in range(10):
        interruptible_sleep(1)
        print(f"Linear task: {input_info} - {i}")


if __name__ == "__main__":
    from task_scheduling.client import submit_task
    from task_scheduling.variable import *

    task_id1 = submit_task(
        None, None, FUNCTION_TYPE_IO, True, "linear_task",
        linear_task, priority_low, "Hello Linear"
    )
```