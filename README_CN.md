- [English version](./README.md)
- [中文版本](./README_CN.md)

# Task Scheduling Library

一个功能强大的Python任务调度库,支持异步和同步任务执行,提供强大的任务管理和监控功能(已支持`NO GIL`)

## 核心功能

- 任务调度: 支持异步代码和同步代码,相同名称的任务自动排队执行
- 任务管理: 强大的任务状态监控和管理能力
- 灵活控制: 支持向执行代码发送(终止,暂停,恢复)命令
- 超时处理: 可为任务启用超时检测,长时间运行的任务会被强制终止
- 状态查询: 通过接口直接获取任务当前状态或者网页控制端
- 智能休眠: 无任务时会自动休眠节省资源
- 优先级管理: 在任务过多时高优先级的任务会优先运行
- 结果获取: 可以获取任务返回的运行结果
- 任务禁用管理: 可以在黑名单中添加任务名称,该名称的任务添加会被阻拦
- 队列任务取消: 可以取消还在排队的同名称的所有任务
- 线程级任务管理(实验性功能): 灵活的任务结构管理
- 任务树模式管理(实验性功能): 当主任务结束,其他所有分支任务都会被销毁
- 依赖型任务执行(实验性功能): 依赖于主任务返回结果运行的函数将启动并运行

## 未来的计划

- 动态调节: 根据负载动态调整配置文件
- 任务重试: 在对应的报错发生时重新尝试运行任务
- 控制界面: 功能更加全面的的网页控制界面

## 安装

```commandline
pip install --upgrade task_scheduling
```

## 命令行运行

### !!!警告!!!

不支持对于任务的精密控制

### 使用示例:

```commandline
python -m task_scheduling

#  The task scheduler starts.
#  Wait for the task to be added.
#  Task status UI available at http://localhost:8000

# 添加命令: -cmd <command> -n <task_name>

-cmd 'python test.py' -n 'test'
#  Parameter: {'command': 'python test.py', 'name': 'test'}
#  Create a success. task ID: 7fc6a50c-46c1-4f71-b3c9-dfacec04f833
#  Wait for the task to be added.
```

使用 `ctrl + c` 退出运行

# 核心API详解

### 对于`NO GIL`的支持

使用python3.14以上的版本开启`NO GIL`既可以使用,运行时会输出`Free threaded is enabled`

运行下面示例在`GIL`和`NO GIL`版本查看速度差别

### 使用示例:

```python
import time
import math


def linear_task(input_info):
    total_start_time = time.time()

    for i in range(18):
        result = 0
        for j in range(1000000):
            result += math.sqrt(j) * math.sin(j) * math.cos(j)

    total_elapsed = time.time() - total_start_time
    print(f"{input_info} - Total time: {total_elapsed:.3f}s")


from task_scheduling.common import set_log_level

set_log_level("DEBUG")

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation
    from task_scheduling.manager import task_scheduler
    from task_scheduling.variable import *

    task_creation(
        None, None, FUNCTION_TYPE_IO, True, "task1",
        linear_task, priority_low, "task1"
    )

    task_creation(
        None, None, FUNCTION_TYPE_IO, True, "task2",
        linear_task, priority_low, "task2"
    )

    task_creation(
        None, None, FUNCTION_TYPE_IO, True, "task3",
        linear_task, priority_low, "task3"
    )

    task_creation(
        None, None, FUNCTION_TYPE_IO, True, "task4",
        linear_task, priority_low, "task4"
    )

    task_creation(
        None, None, FUNCTION_TYPE_IO, True, "task5",
        linear_task, priority_low, "task5"
    )

    task_creation(
        None, None, FUNCTION_TYPE_IO, True, "task6",
        linear_task, priority_low, "task6"
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler(True)
```

## 修改日志等级

### !!!警告!!!

请放在`if __name__ == "__main__":`前面

### 使用示例:

```python
from task_scheduling.common import set_log_level

set_log_level("DEBUG")  # INFO, DEBUG, ERROR, WARNING

if __name__ == "__main__":
    ...
```

## 开启监视页面

网页端可以查看任务状态,运行时间,可以（暂停,终止,恢复）任务

### 使用示例:

```python
from task_scheduling.webui import start_task_status_ui

# Launch the web interface and visit: http://localhost:8000
start_task_status_ui()
```

## 创建任务

- task_creation(delay: int or None, daily_time: str or None, function_type: str, timeout_processing: bool, task_name:
  str, func: Callable, *args, **kwargs) -> str or None:

### 参数说明:

**delay**: 延迟执行时间（秒），用于定时任务(不使用填写None)

**daily_time**: 每日执行时间，格式"HH:MM"，用于定时任务(不使用填写None)

**function_type**: 函数类型 (`FUNCTION_TYPE_IO`, `FUNCTION_TYPE_CPU`, `FUNCTION_TYPE_TIMER`)

**timeout_processing**: 是否启用超时检测和强制终止 (`True`, `False`)

**task_name**: 任务名称，相同名称的任务会排队执行

**func**: 要执行的函数

**priority**: 任务优先级 (`priority_low`, `priority_high`)

**args, kwargs**: 函数参数

返回值: 任务ID字符串

### 使用示例:

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
    from task_scheduling.webui import start_task_status_ui

    start_task_status_ui()

    task_id1 = task_creation(
        None, None, FUNCTION_TYPE_IO, True, "linear_task",
        linear_task, priority_low, "Hello Linear"
    )

    task_id2 = task_creation(
        None, None, FUNCTION_TYPE_IO, True, "async_task",
        async_task, priority_low, "Hello Async"
    )

    task_id3 = task_creation(
        None, None, FUNCTION_TYPE_CPU, True, "linear_task",
        linear_task, priority_low, "Hello Linear"
    )

    task_id4 = task_creation(
        None, None, FUNCTION_TYPE_CPU, True, "async_task",
        async_task, priority_low, "Hello Async"
    )

    task_id5 = task_creation(
        10, None, FUNCTION_TYPE_TIMER, True, "timer_task",
        linear_task, priority_low, "Hello Timer"
    )

    task_id6 = task_creation(
        None, "16:32", FUNCTION_TYPE_TIMER, True, "timer_task",
        linear_task, priority_low, "Hello Timer"
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler(True)

```

## 暂停或恢复任务运行

- pause_api(task_type: str, task_id: str) -> bool:

- resume_api(task_type: str, task_id: str) -> bool:

### !!!警告!!!

任务暂停时候,超时计时器依然在运作,如果需要使用暂停功能建议关闭超时处理,防止当任务恢复时候因为超时被终止

### 参数说明:

**task_type**: 任务所在的调度器 (`CPU_ASYNCIO`, `IO_ASYNCIO`, `CPU_LINER`, `IO_LINER`, `TIMER`)

**task_id**: 要控制的任务ID

返回值: 布尔值，表示操作是否成功

### 使用示例:

```python
import time
from task_scheduling.utils import interruptible_sleep


def long_running_task():
    for i in range(10):
        interruptible_sleep(1)
        print(i)


if __name__ == "__main__":
    from task_scheduling.variable import *
    from task_scheduling.scheduler import pause_api, resume_api
    from task_scheduling.task_creation import task_creation
    from task_scheduling.manager import task_scheduler

    task_id = task_creation(
        None, None, FUNCTION_TYPE_IO, True, "long_task",
        long_running_task, priority_low
    )
    time.sleep(2)
    pause_api(IO_LINER, task_id)
    time.sleep(3)
    resume_api(IO_LINER, task_id)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler(True)
```

## 读取函数类型

- task_function_type.append_to_dict(task_name: str, function_type: str) -> None:

- task_function_type.read_from_dict(task_name: str) -> Optional[str]:

### 函数说明

读取已存储函数的类型或写入，储存文件在:`task_scheduling/function_data/task_type.pkl`

### 参数说明:

**task_name**: 函数名字

**function_type**: 要写入的函数类型(可填写为`scheduler_cpu`, `scheduler_io`)

*args, **kwargs: 函数参数

### 使用示例:

```python
from task_scheduling.mark import task_function_type
from task_scheduling.variable import *

task_function_type.append_to_dict("CPU_Task", FUNCTION_TYPE_CPU)
print(task_function_type.read_from_dict("CPU_Task"))
```

## 获取任务结果

- get_result_api(task_type: str, task_id: str) -> Any:

### 函数说明

返回值: 任务结果，如果未完成则返回None

### 参数说明:

**task_type**: 任务类型

**task_id**: 任务ID

### 使用示例:

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
            print(result)
            break
        time.sleep(1)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler(True)
```

## 获取所有任务状态

- get_tasks_info() -> str:

### 参数说明:

返回值: 包含任务状态的字符串

### 使用示例:

```python
import time
from task_scheduling.variable import *

if __name__ == "__main__":
    from task_scheduling.webui import get_tasks_info
    from task_scheduling.task_creation import task_creation
    from task_scheduling.manager import task_scheduler

    task_creation(None, None, FUNCTION_TYPE_IO, True, "task1", lambda: time.sleep(2), priority_low)
    task_creation(None, None, FUNCTION_TYPE_IO, True, "task2", lambda: time.sleep(3), priority_low)
    time.sleep(1)
    print(get_tasks_info())

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler(True)
```

## 获取特定任务状态

- get_task_status(self, task_id: str) -> Optional[Dict[str, Optional[Union[str, float, bool]]]]:

### 参数说明:

**task_id**: 任务ID

返回值: 包含任务状态的字典

### 使用示例:

```python
import time

if __name__ == "__main__":
    from task_scheduling.manager import task_status_manager, task_scheduler
    from task_scheduling.task_creation import task_creation
    from task_scheduling.variable import *

    task_id = task_creation(
        None, None, FUNCTION_TYPE_IO, True, "status_task",
        lambda: time.sleep(5), priority_low
    )
    time.sleep(1)
    print(task_status_manager.get_task_status(task_id))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler(True)
```

# 获取任务总数

- get_task_count(self, task_name) -> int:

- get_all_task_count(self) -> Dict[str, int]:

### 参数说明:

**task_name**:函数名字

返回值: 字典或者整数

### 使用示例:

```python
import time


def line_task(input_info):
    while True:
        time.sleep(1)
        print(input_info)


input_info = "running..."

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation
    from task_scheduling.manager import task_status_manager, task_scheduler
    from task_scheduling.variable import *

    task_id1 = task_creation(None, None, FUNCTION_TYPE_IO, True, "task1", line_task, priority_low, input_info)

    print(task_status_manager.get_task_count("task1"))
    print(task_status_manager.get_all_task_count())

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler(True)
```

## 强制终止运行任务。

- kill_api(task_type: str, task_id: str) -> bool

### !!!警告!!!

代码不支持终止堵塞型任务,对于`time.sleep`给出了替代的版本,当要进行长时间等待请使用`interruptible_sleep`,异步代码使用
`await asyncio.sleep`

### 参数说明:

**task_type**: 任务类型

**task_id**: 要终止的任务ID

返回值: 布尔值，表示终止是否成功

### 使用示例:

```python
import time
from task_scheduling.variable import *
from task_scheduling.utils import interruptible_sleep


def infinite_task():
    while True:
        interruptible_sleep(1)
        print("running...")


if __name__ == "__main__":
    from task_scheduling.scheduler import kill_api
    from task_scheduling.task_creation import task_creation
    from task_scheduling.manager import task_scheduler

    task_id = task_creation(
        None, None, FUNCTION_TYPE_IO, True, "infinite_task",
        infinite_task, priority_low
    )
    time.sleep(3)
    kill_api(IO_LINER, task_id)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler(True)
```

## 添加或删除禁用任务名称

- task_scheduler.add_ban_task_name(task_name: str) -> None:

- task_scheduler.remove_ban_task_name(task_name: str) -> None:

### 函数说明

当添加某类任务名称之后,该类任务将会被拦截阻止运行

### 参数说明:

**task_name**:函数名字

### 使用示例:

```python
import time


def line_task(input_info):
    while True:
        time.sleep(1)
        print(input_info)


input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation
    from task_scheduling.manager import task_scheduler
    from task_scheduling.webui import start_task_status_ui
    from task_scheduling.variable import *

    start_task_status_ui()

    task_id1 = task_creation(None, None, FUNCTION_TYPE_IO, True, "task1", line_task, priority_low, input_info)
    task_scheduler.add_ban_task_name("task1")
    task_id2 = task_creation(None, None, FUNCTION_TYPE_IO, True, "task1", line_task, priority_low, input_info)
    task_scheduler.remove_ban_task_name("task1")
    task_id3 = task_creation(None, None, FUNCTION_TYPE_IO, True, "task1", line_task, priority_low, "1111")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler(True)
```

## 取消队列中某类任务

- cancel_the_queue_task_by_name(self, task_name: str) -> None:

### 参数说明:

**task_name**:函数名字

### 使用示例:

```python
import time


def line_task(input_info):
    while True:
        time.sleep(1)
        print(input_info)


input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation
    from task_scheduling.manager import task_scheduler
    from task_scheduling.webui import start_task_status_ui
    from task_scheduling.variable import *

    start_task_status_ui()

    task_id1 = task_creation(None, None, FUNCTION_TYPE_IO, True, "task1", line_task, priority_low, input_info)
    task_id2 = task_creation(None, None, FUNCTION_TYPE_IO, True, "task1", line_task, priority_low, input_info)
    time.sleep(1)

    task_scheduler.cancel_the_queue_task_by_name("task1")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler(True)
```

## 关闭调度器

- shutdown_scheduler(force_cleanup: bool) -> None:

### !!!警告!!!

在关闭运行前必须执行该函数去结束和清理运行任务

### 参数说明:

**force_cleanup**:是否等待剩下任务运行

### 使用示例:

```python
from task_scheduling.manager import task_scheduler

task_scheduler.shutdown_scheduler(True)
```

## 临时更新配置文件参数(热加载)

- update_config(key: str, value: Any) -> Any:

### !!!警告!!!

请放在`if __name__ == "__main__":`前面

### 参数说明:

**key**: 键

**value**: 值

返回值:True或者报错信息

### 使用示例:

```python
from task_scheduling.common import update_config

key, value = None
update_config(key, value)
if __name__ == "__main__":
    ...
```

## 线程级任务管理(实验性功能)

### !!!警告!!!

!!!该功能只支持CPU密集型线性任务!!!

### 功能说明:

`线程级任务管理(实验性功能)`默认为关闭状态,当配置文件中`thread_management=True`开启该功能

`main_task`中前三位接受参数必须为`share_info`, `_sharedtaskdict`, `task_signal_transmission`(
如果开启了该功能,正常任务也可以使用,只需要不传入前面所说的三个参数)

`@wait_branch_thread_ended`必须放在main_task上面，防止主线程结束,分支线程还没运行完导致错误

`other_task`为需要运行的分支线程,上面必须添加`@branch_thread_control`装饰器来控制和监视

`@branch_thread_control`装饰器接收参数`share_info`, `_sharedtaskdict`, `timeout_processing`, `task_name`

`task_name`必须是唯一不重复的,用于获取其他分支线程的task_id(使用`_sharedtaskdict.read(task_name)`
获取task_id去终止，暂停或恢复)

使用`threading.Thread`语句必须添加`daemon=True`将线程设置为守护线程(
没有添加会让关闭操作时间增加,反正主线程结束,会强制终止所有分支线程)

所有的分支线程都可以在网页端查看到运行状态(开启网页端请使用`start_task_status_ui()`)

这里提供两个控制函数:

在主线程内使用`task_signal_transmission[_sharedtaskdict.read(task_name)] = ["action"]` action可以填写为`kill`, `pause`,
`resume`, 也可以按顺序填写几个操作

在主线程外部可以使用`kill_api()`

### 使用示例:

```python
import threading
import time
from task_scheduling.utils import wait_branch_thread_ended, branch_thread_control


@wait_branch_thread_ended
def main_task(share_info, sharedtaskdict, task_signal_transmission, input_info):
    task_name = "other_task"
    timeout_processing = True

    @branch_thread_control(share_info, sharedtaskdict, timeout_processing, task_name)
    def other_task(input_info):
        while True:
            time.sleep(1)
            print(input_info)

    threading.Thread(target=other_task, args=(input_info,), daemon=True).start()

    # Use this statement to terminate the branch thread
    # time.sleep(4)
    # task_signal_transmission[sharedtaskdict.read(task_name)] = ["kill"]


from task_scheduling.common import update_config

update_config("thread_management", True)

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation
    from task_scheduling.manager import task_scheduler
    from task_scheduling.webui import start_task_status_ui
    from task_scheduling.variable import *

    start_task_status_ui()

    task_id1 = task_creation(
        None, None, FUNCTION_TYPE_CPU, True, "linear_task",
        main_task, priority_low, "test")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler(True)
```

## 任务树模式管理(实验性功能)

### 功能说明

字典中的任务名字将会以`task_group_name|task_name`显示,当名字任务为`task_group_name`被结束,所有的以
`task_group_name|task_name`显示的任务都会一并结束,`task_group`是这个任务树中的主任务(该任务实际只是一个载体,没有功能)

### 参数说明

**task_group_name**:  这个任务树中的主任务名字((该任务实际只是一个载体,没有功能),所有的分支任务都会加上该主任务的名字

**task_dict**: `键`存储任务名字,`值`存储要执行的函数,是否启用超时检测强制终止 (`True`, `False`) 和函数需要的参数 (
必须按照顺序)

### 使用示例:

```python
import time


def liner_task(input_info):
    while True:
        time.sleep(1)
        print(input_info)


from task_scheduling.common import update_config

update_config("thread_management", True)
if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation
    from task_scheduling.manager import task_scheduler
    from task_scheduling.quick_creation import task_group
    from task_scheduling.webui import start_task_status_ui
    from task_scheduling.variable import *

    start_task_status_ui()

    task_group_name = "main_task"

    task_dict = {
        "task1": (liner_task, True, 1111),
        "task2": (liner_task, True, 2222),
        "task3": (liner_task, True, 3333),
    }

    task_id1 = task_creation(
        None, None, FUNCTION_TYPE_CPU, True, task_group_name,
        task_group, priority_low, task_group_name, task_dict)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler(True)
```

## 依赖型任务执行(实验性功能)

- task_dependency_manager(main_task_id: str, dependent_task: Callable, *args) -> None:

### !!!警告!!!

如果主任务要传回参数,必须为元组格式,不接受其他格式的参数.

### 功能说明

使用`task_creation`创建完主任务后,使用`task_dependency_manager`类设置依赖于主任务返回结果的运行函数.类的方法有
`after_completion`:主任务完成后运行(返回值不必须), `after_cancel`:主任务被取消后运行, `after_timeout`:主任务超时后运行,
`after_error`:
主任务错误后运行

`main_task_id`填写主任务的任务id由task_creation传回

`dependent_task`填写要运行的依赖任务.

后面为依赖任务需要的参数,主任务传回的参数在最后面,依赖任务参数前6位填写为

`task_creation`所需要的六个参数：

**delay**: 延迟执行时间（秒），用于定时任务(不使用填写None)

**daily_time**: 每日执行时间，格式"HH:MM"，用于定时任务(不使用填写None)

**function_type**: 函数类型 (`FUNCTION_TYPE_IO`, `FUNCTION_TYPE_CPU`, `FUNCTION_TYPE_TIMER`)

**timeout_processing**: 是否启用超时检测和强制终止 (`True`, `False`)

**func**: 要执行的函数

**priority**: 任务优先级 (`priority_low`, `priority_high`)

### 参数说明

**main_task_id**: 主任务的任务id

**dependent_task**: 要运行的依赖任务

**args**: 依赖任务需要的参数,主任务传回的参数会在最后面.

### 使用示例:

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
    from task_scheduling.followup_creation import task_dependency_manager
    from task_scheduling.webui import start_task_status_ui
    from task_scheduling.variable import *

    start_task_status_ui()

    task_id1 = task_creation(None, None, FUNCTION_TYPE_IO, True, "mian_task", mian_task, priority_low, "test1")

    task_dependency_manager.after_completion(task_id1, dependent_task,
                                             None, None, FUNCTION_TYPE_IO, True, "dependent_task", priority_low,
                                             "test2")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler(True)
```

## 网页控制端

![01.png](./img/01.png)

Task status UI available at http://localhost:8000

- 观察任务运行状态并控制任务(`终止`,`暂停`,`恢复`)

## 配置

文件存储在:`task_scheduling/config/config.yaml`

同名称的 CPU 密集型异步任务可以运行的最大数量

`cpu_asyncio_task: 8`

IO 密集型异步任务运行最大任务数

`io_asyncio_task: 20`

CPU 密集型线性任务中运行最大任务数

`cpu_liner_task: 20`

IO 密集型线性任务中运行最大任务数

`io_liner_task: 20`

定时器执行最多任务数

`timer_task: 20`

当多长时间没有任务时,关闭任务调度器(秒)

`max_idle_time: 600`

当任务运行多久而未完成时,强制结束(秒)

`watch_dog_time: 120`

任务状态存储器中最大存储任务数

`maximum_task_info_storage: 40`

多久检查存储器中任务状态是否正确(秒)

`status_check_interval: 800`

单个调度器最大储存返回结果数量Maximum number of returned results that a single scheduler can store

`maximum_result_storage`: 20,

多久清理一次返回结果储存(秒)How often to clear the return result storage (seconds)

`maximum_result_time_storage`: 16,

是否在 CPU 密集型线性任务中启用超级线程管理

`thread_management: False`

是否应该抛出异常而不捕获以便定位错误

`exception_thrown: False`

### 如果你有更好的想法，欢迎提交一个 PR

## 参考库：

为了便于后续修改,有些文件是直接放入文件夹,而不是通过 pip
安装的,所以这里明确说明了使用的库:https://github.com/glenfant/stopit