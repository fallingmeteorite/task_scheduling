## 依赖性任务本地(设置某个任务出现什么情况后执行的任务)

task_dependency_local(main_task_id: str, dependent_task: Callable, *args) -> None

- 警告:

如果主任务要传回参数,必须为元组格式,不接受其他格式的参数.

- 功能说明:

使用`task_creation`创建完主任务后,使用`task_dependency_local`类设置依赖于主任务返回结果的运行函数。

- 可用方法:

`after_completion`: 主任务完成后运行(返回值不必须)

`after_cancel`: 主任务被取消后运行

`after_timeout`: 主任务超时后运行

`after_error`: 主任务错误后运行

- 参数说明:

**main_task_id**: 主任务的任务id

**dependent_task**: 要运行的依赖任务

**args**: 依赖任务需要的参数,主任务传回的参数会在最后面

- 依赖任务参数说明:

依赖任务参数前6位必须填写为`task_creation`所需要的六个参数：

**delay**: 延迟执行时间（秒），用于定时任务(不使用填写None)

**daily_time**: 每日执行时间，格式"HH:MM"，用于定时任务(不使用填写None)

**function_type**: 函数类型 (`FUNCTION_TYPE_IO`, `FUNCTION_TYPE_CPU`, `FUNCTION_TYPE_TIMER`)

**timeout_processing**: 是否启用超时检测和强制终止 (`True`, `False`)

**func**: 要执行的函数

**priority**: 任务优先级 (`priority_low`, `priority_high`)

- 使用示例:

```python
import time


def mian_task(input_info):
    time.sleep(2.0)
    return input_info,


def dependent_task(input_info, return_value=None):
    print(input_info, return_value)


if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation
    from task_scheduling.manager import task_scheduler
    from task_scheduling.construct import task_dependency_local
    from task_scheduling.server_webui import start_task_status_ui
    from task_scheduling.variable import *

    start_task_status_ui()

    task_id1 = task_creation(None, None, FUNCTION_TYPE_IO, True, "mian_task", mian_task, priority_low, "test1")

    # 设置主任务完成后的依赖任务
    task_dependency_local.after_completion(task_id1, dependent_task,
                                           None, None, FUNCTION_TYPE_IO, True, "dependent_task", priority_low,
                                           "test2")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler()
```

## 依赖性任务网络(设置某个任务出现什么情况后执行的任务)

task_dependency_network(main_task_id: str, dependent_task: Callable, *args) -> None

- 警告:

如果主任务要传回参数,必须为元组格式,不接受其他格式的参数.该功能要`network_storage_results`为`true`

- 功能说明:

使用`task_creation`创建完主任务后,使用`task_dependency_network`类设置依赖于主任务返回结果的运行函数。

- 可用方法:

`after_completion`: 主任务完成后运行(返回值不必须)

`after_cancel`: 主任务被取消后运行

`after_timeout`: 主任务超时后运行

`after_error`: 主任务错误后运行

- 参数说明:

**main_task_id**: 主任务的任务id

**dependent_task**: 要运行的依赖任务

**args**: 依赖任务需要的参数,主任务传回的参数会在最后面

- 依赖任务参数说明:

依赖任务参数前6位必须填写为`task_creation`所需要的六个参数：

**delay**: 延迟执行时间（秒），用于定时任务(不使用填写None)

**daily_time**: 每日执行时间，格式"HH:MM"，用于定时任务(不使用填写None)

**function_type**: 函数类型 (`FUNCTION_TYPE_IO`, `FUNCTION_TYPE_CPU`, `FUNCTION_TYPE_TIMER`)

**timeout_processing**: 是否启用超时检测和强制终止 (`True`, `False`)

**func**: 要执行的函数

**priority**: 任务优先级 (`priority_low`, `priority_high`)

- 使用示例:

```python
def mian_task(input_info):
    import time
    time.sleep(2.0)
    return input_info,


def dependent_task(input_info, return_value=None):
    print(input_info, return_value)


if __name__ == "__main__":
    from task_scheduling.client import submit_task
    from task_scheduling.construct import task_dependency_network
    from task_scheduling.result_server import result_server
    from task_scheduling.variable import *
    import time

    result_server.start_server()

    task_id1 = submit_task(None, None, FUNCTION_TYPE_IO, True, "mian_task", mian_task, priority_low, "test1")

    # 设置主任务完成后的依赖任务
    task_dependency_network.after_completion(task_id1, dependent_task,
                                             None, None, FUNCTION_TYPE_IO, True, "dependent_task", priority_low,
                                             "test2")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
```