## 同步获取任务结果

get_result_api(task_type: str, task_id: str) -> Any
**!!!该函数可能已经过时!!!**

- 参数说明:

**task_type**: 任务类型

**task_id**: 任务ID

**返回**: 任务结果,如果未完成则返回None

- 使用示例

```python
import time
from task_scheduling.variable import *


def calculation_task(x, y):
    return x * y


if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation
    from task_scheduling.manager import task_scheduler
    from task_scheduling.scheduler import get_result_api

    task_id = task_creation(
        None, None, FUNCTION_TYPE_IO, True, "long_task",
        calculation_task, priority_low, 5, 10
    )

    while True:
        result = get_result_api(IO_LINER, task_id)
        if result is not None:
            print(result)  # 输出: 50
            break
        time.sleep(1)
```

## 异步方式获取结果

get_task_result(task_id: str) -> Any
**!!!该函数是异步函数,请在事件循环中使用!!!**

- 参数说明:

**task_id**: 任务ID

**返回**: 任务结果,如果未完成则返回None

- 使用示例

```python
import asyncio
import time
from task_scheduling.variable import *


def calculation_task(x, y):
    time.sleep(4)
    return x * y


async def main_async():
    from task_scheduling.task_creation import task_creation
    from task_scheduling.utils import get_task_result

    task_id1 = task_creation(
        None, None, FUNCTION_TYPE_IO, True, "linear_task",
        calculation_task, priority_low, 5, 10
    )

    result = await get_task_result(task_id1)
    print(result)  # 输出: 50
    return result


if __name__ == "__main__":
    from task_scheduling.manager import task_scheduler
    from task_scheduling.get_service import result_server

    # 启动结果存储服务器
    result_server.start_server()

    try:
        asyncio.run(main_async())
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler()
```