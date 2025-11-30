## 重试装饰器

retry_on_error(exceptions: Union[Type[Exception], Tuple[Type[Exception], ...], None], max_attempts: int, delay:
Union[float, int]) -> Any

- 参数说明:

**exceptions**: 当什么错误类型发生才开始重试

**max_attempts**: 最大尝试次数

**delay**: 每次重试的间隔时间

- 使用示例:

```python
import time
from task_scheduling.utils import retry_on_error


@retry_on_error(exceptions=(TypeError), max_attempts=3, delay=1.0)
def linear_task(input_info):
    while True:
        print(input_info)
        time.sleep(input_info)


from task_scheduling.common import set_log_level

set_log_level("DEBUG")

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation
    from task_scheduling.manager import task_scheduler
    from task_scheduling.variable import *

    task_creation(
        None, None, FUNCTION_TYPE_CPU, True, "task1",
        linear_task, priority_low, "test"
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler()
```