# 创建任务

## 基本函数

- `task_creation(delay: int or None, daily_time: str or None, function_type: str, timeout_processing: bool, task_name: str, func: Callable, *args, **kwargs) -> str or None`

### !!!警告!!!

`Windows`,`Linux`,`Mac`在多进程中都统一使用`spawn`

IO异步任务将不会通过任务名字排队,将提交后交给时间循环管理,其他任务都会通过名字排队执行

### 参数说明:

**delay**: 延迟执行时间（秒），用于定时任务(不使用填写None)

**daily_time**: 每日执行时间，格式"HH:MM"，用于定时任务(不使用填写None)

**function_type**: 函数类型 (`FUNCTION_TYPE_IO`, `FUNCTION_TYPE_CPU`, `FUNCTION_TYPE_TIMER`)

**timeout_processing**: 是否启用超时终止 (`True`, `False`)

**task_name**: 任务名称，相同名称的任务会排队执行

**func**: 要执行的函数

**priority**: 任务优先级 (`priority_low`, `priority_high`)

**args, kwargs**: 函数参数

返回值: 任务ID字符串

## 使用示例

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
