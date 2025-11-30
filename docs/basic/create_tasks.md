## 任务创建函数

task_creation(delay: int or None, daily_time: str or None, function_type: str, timeout_processing: bool, task_name:
str, func: Callable, *args, **kwargs) -> str or None

- 警告:

`Windows`,`Linux`,`Mac`在多进程中都统一使用`spawn`

IO异步任务中将不会阻拦同名任务执行,将提交后交给事件循环管理,其他任务中的同名任务都会排队执行

- 参数说明:

**delay**: 延迟执行时间(秒),用于定时任务(不使用填写None)

**daily_time**: 每日执行时间,格式"HH:MM",用于定时任务(不使用填写None),使用24小时制

**function_type**: 函数类型 (`FUNCTION_TYPE_IO`, `FUNCTION_TYPE_CPU`, `FUNCTION_TYPE_TIMER`)

**timeout_processing**: 是否启用超时终止 (`True`, `False`)

**task_name**: 任务名称,相同名称的任务会排队执行

**func**: 要执行的函数

**priority**: 任务优先级 (`priority_low`, `priority_high`)

**args, kwargs**: 函数参数

**返回**: 任务ID字符串

- 使用示例:

```python
import asyncio
import time
from task_scheduling.variable import *
from task_scheduling.utils import interruptible_sleep


def linear_task(input_info):
    for i in range(10):
        interruptible_sleep(1)
        print(f"Linear task: {input_info} - {i}")


async def async_task(input_info):
    for i in range(10):
        await asyncio.sleep(1)
        print(f"Async task: {input_info} - {i}")


if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation
    from task_scheduling.manager import task_scheduler
    from task_scheduling.server_webui import start_task_status_ui

    start_task_status_ui()

    task_id1 = task_creation(
        None, None, FUNCTION_TYPE_IO, True, "linear_task",
        linear_task, priority_low, "Hello Linear"
    )

    task_id2 = task_creation(
        None, None, FUNCTION_TYPE_IO, True, "async_task",
        async_task, priority_low, "Hello Async"
    )
    while True:
        try:
            time.sleep(0.1)
        except KeyboardInterrupt:
            task_scheduler.shutdown_scheduler()
```

## 命令任务提交

- 警告：

不支持对于任务的精密控制

- 使用示例:

```
python -m task_scheduling

# The task scheduler starts.
# Wait for the task to be added.
# Task status UI available at http://localhost:8000

# 添加命令: -cmd <command> -n <task_name>

-cmd 'python test.py' -n 'test'
# Parameter: {'command': 'python test.py', 'name': 'test'}
# Create a success. task ID: 7fc6a50c-46c1-4f71-b3c9-dfacec04f833
# Wait for the task to be added.
# 使用 `ctrl + c` 退出运行
```

