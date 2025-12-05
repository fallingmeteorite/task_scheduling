## 获取所有任务状态

get_tasks_info() -> str

- 参数说明:

**返回**: 包含任务状态的字符串

- 使用示例:

```python
import time

from task_scheduling.variable import *

if __name__ == "__main__":
    from task_scheduling.client import RPCClient
    from task_scheduling.task_creation import task_creation

    task_creation(None, None, FUNCTION_TYPE_IO, True, "task1", lambda: time.sleep(2), priority_low)
    task_creation(None, None, FUNCTION_TYPE_IO, True, "task2", lambda: time.sleep(3), priority_low)

    time.sleep(1)
    with RPCClient() as client:
        # 获取所有任务状态
        print(client.get_tasks_info())
```

## 获取特定任务状态

get_task_status(task_id: str) -> Optional[Dict[str, Optional[Union[str, float, bool]]]]

- 参数说明:

**task_id**: 任务ID

**返回**: 包含任务状态的字典

- 使用示例:

```python
import time

from task_scheduling.variable import *

if __name__ == "__main__":
    from task_scheduling.client import RPCClient
    from task_scheduling.task_creation import task_creation

    task_creation(None, None, FUNCTION_TYPE_IO, True, "task1", lambda: time.sleep(2), priority_low)
    task_creation(None, None, FUNCTION_TYPE_IO, True, "task2", lambda: time.sleep(3), priority_low)

    time.sleep(1)
    with RPCClient() as client:
        # 获取特定任务状态
        task_id = "your_task_id_here"
        print(client.get_task_status(task_id))
```

## 获取任务总数

get_task_count(task_name) -> int

get_all_task_count() -> Dict[str, int]

- 参数说明:

**task_name**: 函数名字

**返回**: 字典或者整数

- 使用示例:

```python
import time
from task_scheduling.variable import *

if __name__ == "__main__":
    from task_scheduling.client import RPCClient
    from task_scheduling.task_creation import task_creation

    task_creation(None, None, FUNCTION_TYPE_IO, True, "task1", lambda: time.sleep(2), priority_low)
    task_creation(None, None, FUNCTION_TYPE_IO, True, "task2", lambda: time.sleep(3), priority_low)

    time.sleep(1)
    with RPCClient() as client:
        # 获取任务计数
        print(client.get_task_count("task1"))
        print(client.get_all_task_count())
```