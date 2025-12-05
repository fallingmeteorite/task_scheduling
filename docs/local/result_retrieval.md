## 同步获取任务结果

get_result_api(task_type: str, task_id: str) -> Any
**!!!该函数不是很优秀,建议查看网络功能中的结果获取方法!!!**

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