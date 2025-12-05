## 添加或删除禁用任务名称

add_ban_task_name(task_name: str) -> None

remove_ban_task_name(task_name: str) -> None

- 警告:

已经进入调度器的任务将不会被处理，只有在任务状态为`queued`才会被取消

- 参数说明:

**task_name**: 函数名字

- 使用示例:

```python
import time


def line_task(input_info):
    while True:
        time.sleep(1)
        print(input_info)


input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation
    from task_scheduling.client import RPCClient
    from task_scheduling.variable import *

    # 创建第一个任务
    task_id1 = task_creation(None, None, FUNCTION_TYPE_IO, True, "task1", line_task, priority_low, input_info)
    with RPCClient() as client:
        # 添加任务名称到黑名单
        client.add_ban_task_name("task1")

    # 这个任务将被拦截
    task_id2 = task_creation(None, None, FUNCTION_TYPE_IO, True, "task1", line_task, priority_low, input_info)
    with RPCClient() as client:
        # 从黑名单移除
        client.remove_ban_task_name("task1")

    # 这个任务可以正常创建
    task_id3 = task_creation(None, None, FUNCTION_TYPE_IO, True, "task1", line_task, priority_low, "1111")
```

## 取消队列中某类任务

cancel_the_queue_task_by_name(task_name: str) -> None

- 警告:

已经进入调度器的任务将不会被处理，只有在任务状态为`queued`才会被取消

- 参数说明:

**task_name**: 函数名字

- 使用示例:

```python
import time


def line_task(input_info):
    while True:
        time.sleep(1)
        print(input_info)


input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation
    from task_scheduling.client import RPCClient
    from task_scheduling.variable import *

    # 创建第一个任务
    task_id1 = task_creation(None, None, FUNCTION_TYPE_IO, True, "task1", line_task, priority_low, input_info)
    with RPCClient() as client:
        # 取消队列中的任务
        client.cancel_the_queue_task_by_name("task1")
```