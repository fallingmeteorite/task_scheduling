## 暂停或恢复任务运行

pause_api(task_type: str, task_id: str) -> bool

resume_api(task_type: str, task_id: str) -> bool

- 警告:

任务暂停时候,超时计时器依然在运作,如果需要使用暂停功能建议关闭超时处理,防止当任务恢复时候因为超时被终止,在`Linux`,`Mac`
中不支持线程任务暂停恢复,只支持进程进程任务,暂停将暂停整个进程的任务

- 参数说明:

**task_type**: 任务所在的调度器 (`CPU_ASYNCIO`, `IO_ASYNCIO`, `CPU_LINER`, `IO_LINER`, `TIMER`)

**task_id**: 要控制的任务ID

**返回**: 布尔值，表示操作是否成功

- 使用示例:

```python
import time
from task_scheduling.variable import *
from task_scheduling.utils import interruptible_sleep


def long_running_task():
    for i in range(10):
        interruptible_sleep(1)
        print(i)


if __name__ == "__main__":
    from task_scheduling.client import RPCClient
    from task_scheduling.task_creation import task_creation

    task_id = task_creation(
        None, None, FUNCTION_TYPE_IO, True, "long_task",
        long_running_task, priority_low
    )
    with RPCClient() as client:
        time.sleep(2)
        client.pause_api(IO_LINER, task_id)  # 暂停任务
        time.sleep(2)
        client.resume_api(IO_LINER, task_id)  # 恢复任务
```

## 强制终止运行任务

kill_api(task_type: str, task_id: str) -> bool

- 警告:

代码不支持终止堵塞型任务,对于`time.sleep`给出了替代的版本,当要进行长时间等待请使用`interruptible_sleep`,异步代码使用
`await asyncio.sleep`

- 参数说明:

**task_type**: 任务类型

**task_id**: 要终止的任务ID

**返回**: 布尔值，表示终止是否成功

- 使用示例:

```python
import time

from task_scheduling.utils import interruptible_sleep
from task_scheduling.variable import *


def long_running_task():
    for i in range(10):
        interruptible_sleep(1)
        print(i)


if __name__ == "__main__":
    from task_scheduling.client import RPCClient
    from task_scheduling.task_creation import task_creation

    task_id = task_creation(
        None, None, FUNCTION_TYPE_IO, True, "long_task",
        long_running_task, priority_low
    )
    with RPCClient() as client:
        time.sleep(2)
        client.kill_api(IO_LINER, task_id)  # 终止任务
```