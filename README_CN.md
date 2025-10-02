- [English version](./README.md)
- [中文版本](./README_CN.md)

# Task Scheduling Library

一个功能强大的Python任务调度库,支持异步和同步任务执行,提供强大的任务管理和监控功能

## 功能特性

### 核心功能

- 任务调度: 支持异步代码和同步代码,相同类型的任务自动排队执行

- 任务管理: 强大的任务状态监控和管理能力
- 灵活终止: 支持向执行代码发送终止命令
- 超时处理: 可为任务启用超时检测,长时间运行的任务会被强制终止
- 禁用列表: 运行失败的任务可加入禁用列表，避免重复执行
- 状态查询: 通过接口直接获取任务当前状态(完成,错误,超时等)
- 智能休眠: 无任务时自动休眠节省资源

### 高级特性

- 任务优先级管理(低优先级/高优先级)
- 任务暂停与恢复
- 任务结果获取
- 禁用任务管理
- 队列任务取消
- 线程级任务管理(实验性功能)

### 警告

- 代码不支持终止堵塞任务,比如写入,网络请求,请务必添加对应逻辑比如超时中断,对于运算任务和其他任务只要没有堵塞(
  即代码还在运行而不是等待即可终止)
- 对于time.sleep,库给出了替代的版本,当要进行长时间等待请使用`interruptible_sleep`,异步代码使用`await asyncio.sleep`
- 如果需要检查错误和查找报错位置,请设置日志等级为`set_log_level("DEBUG")`,设置配置文件`exception_thrown: True`
- 下面介绍的函数对于4个调度器都适用，特殊的函数的将会专门标记

## 安装

```
pip install --upgrade task_scheduling
```

## 命令行运行

!!!不支持对于任务的精密控制!!!

```
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

## 核心API详解

### 使用示例:

- 修改日志等级

请放在`if __name__ == "__main__":`前面

```
from task_scheduling.common import set_log_level

set_log_level("DEBUG") # INFO, DEBUG, ERROR, WARNING

if __name__ == "__main__":
    ......
```

- 开启监视页面

```
from task_scheduling.task_info import start_task_status_ui

# Launch the web interface and visit: http://localhost:8000
start_task_status_ui()
```

- task_creation(delay: int or None, daily_time: str or None, function_type: str, timeout_processing: bool, task_name:
  str, func: Callable, *args, **kwargs) -> str or None:

创建并调度任务执行

参数说明:

**delay**: 延迟执行时间（秒），用于定时任务

**daily_time**: 每日执行时间，格式"HH:MM"，用于定时任务

**function_type**: 函数类型 (`scheduler_io`, `scheduler_cpu`, `scheduler_timer`)

**timeout_processing**: 是否启用超时检测和强制终止 (`True`, `False`)

**task_name**: 任务名称，相同名称的任务会排队执行

**func**: 要执行的函数

**priority**: 任务优先级 (`priority_low`, `priority_high`)

*args, **kwargs: 函数参数

返回值: 任务ID字符串

### 使用示例:

```
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
    from task_scheduling.task_creation import task_creation, shutdown

    task_id1 = task_creation(
        None, None, scheduler_io, True, "linear_task", 
        linear_task, priority_low, "Hello Linear"
    )
    
    task_id2 = task_creation(
        None, None, scheduler_io, True, "async_task",
        async_task, priority_low, "Hello Async"
    )
    
    print(task_id1, task_id2)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(True)
```

- pause_and_resume_task(self, task_id: str, action: str) -> bool:

暂停或恢复运行中的任务

参数说明:

**task_id**: 要控制的任务ID

**action**: (可填写`pause`, `resume`)

返回值: 布尔值，表示操作是否成功

### 使用示例:

```
import time
from task_scheduling.variable import *
from task_scheduling.utils import interruptible_sleep


def long_running_task():
    for i in range(10):
        interruptible_sleep(1)
        print(i)


if __name__ == "__main__":
    from task_scheduling.scheduler import io_liner_task
    from task_scheduling.task_creation import task_creation, shutdown

    task_id = task_creation(
        None, None, scheduler_io, True, "long_task",
        long_running_task, priority_low
    )
    time.sleep(2)
    io_liner_task.pause_and_resume_task(task_id, "pause")  
    time.sleep(3)
    io_liner_task.pause_and_resume_task(task_id, "resume")  

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(True)
```

- FunctionRunner(self, func: Callable, task_name: str, *args, **kwargs) -> None:

检查函数类型并记录仪(一共两个类型`scheduler_cpu`, `scheduler_io`)

参数说明:

**func**:要检测的函数

**task_name**:函数名字

*args, **kwargs:函数参数

### 使用示例:

```
import time

import numpy as np


def example_cpu_intensive_function(size, iterations):
    start_time = time.time()
    for _ in range(iterations):
        # Create two random matrices
        matrix_a = np.random.rand(size, size)
        matrix_b = np.random.rand(size, size)
        # Perform matrix multiplication
        np.dot(matrix_a, matrix_b)
    end_time = time.time()
    print(
        f"It took {end_time - start_time:.2f} seconds to calculate {iterations} times {size} times {size} matrix multiplication")


async def example_io_intensive_function():
    for i in range(5):
        with open(f"temp_file_{i}.txt", "w") as f:
            f.write("Hello, World!" * 1000000)
        time.sleep(1)


if __name__ == "__main__":
    from task_scheduling.task_data import FunctionRunner

    cpu_runner = FunctionRunner(example_cpu_intensive_function, "CPU_Task", 10000, 2)
    cpu_runner.run()

    io_runner = FunctionRunner(example_io_intensive_function, "IO_Task")
    io_runner.run()
```

- task_function_type.append_to_dict(task_name: str, function_type: str) -> None:

- task_function_type.read_from_dict(task_name: str) -> Optional[str]:

读取已存储函数的类型或写入，储存文件:`task_scheduling/function_data/task_type.pkl`

参数说明:

**task_name**:函数名字

**function_type**:要写入的函数类型(可填写为`scheduler_cpu`, `scheduler_io`)

*args, **kwargs:函数参数

### 使用示例:

```
from task_scheduling.task_data task_function_type
from task_scheduling.variable import *

task_function_type.append_to_dict("CPU_Task", scheduler_cpu)
print(task_function_type.read_from_dict("CPU_Task"))

```

- get_task_result(task_id: str) -> Optional[Any]:

获取已完成任务的返回值。

参数说明:

**task_id**: 任务ID

返回值: 任务结果，如果未完成则返回None

### 使用示例:

```
import time
from task_scheduling.variable import *


def calculation_task(x, y):
    return x * y


if __name__ == "__main__":
    from task_scheduling.scheduler import io_liner_task
    from task_scheduling.task_creation import task_creation, shutdown

    task_id = task_creation(
        None, None, scheduler_io, True, "long_task",
        calculation_task, priority_low, 5, 10
    )

    while True:
        result = io_liner_task.get_task_result(task_id)
        if result is not None:
            print(result) 
            break
        time.sleep(1)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(True)
```

- get_tasks_info() -> str:

获取所有任务的信息。

返回值: 包含任务信息的格式化字符串

### 使用示例:

```
import time
from task_scheduling.variable import *

if __name__ == "__main__":
    from task_scheduling.task_info import get_tasks_info
    from task_scheduling.task_creation import task_creation, shutdown

    task_creation(None, None, scheduler_io, True, "task1", lambda: time.sleep(2), priority_low)
    task_creation(None, None, scheduler_io, True, "task2", lambda: time.sleep(3), priority_low)
    time.sleep(1)
    print(get_tasks_info())

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(True)
```

- get_task_status(self, task_id: str) -> Optional[Dict[str, Optional[Union[str, float, bool]]]]:

获取特定任务的详细状态信息。

参数说明:

- task_id: 任务ID

返回值: 包含任务状态信息的字典

### 使用示例:

```
import time
from task_scheduling.variable import *

if __name__ == "__main__":
    from task_scheduling.scheduler_management import task_status_manager
    from task_scheduling.task_creation import task_creation, shutdown

    task_id = task_creation(
        None, None, scheduler_io, True, "status_task",
        lambda: time.sleep(5), priority_low
    )
    time.sleep(1)
    print(task_status_manager.get_task_status(task_id))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(True)
```

- get_task_count(self, task_name) -> int:

- get_all_task_count(self) -> Dict[str, int]:

获取任务的总存在

参数说明:

**task_name**:函数名字

返回值: 字典或者整数

### 使用示例:

```
import time


def line_task(input_info):
    while True:
        time.sleep(1)
        print(input_info)


input_info = "running..."

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown
    from task_scheduling.scheduler_management import task_status_manager
    from task_scheduling.variable import *

    task_id1 = task_creation(None,
                             None,
                             scheduler_io,
                             True,
                             "task1",
                             line_task,
                             priority_low,
                             input_info)

    print(task_status_manager.get_task_count("task1"))
    print(task_status_manager.get_all_task_count())

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(True)

```

- force_stop_task(task_id: str, main_task: bool) -> bool:

强制终止运行中的任务。

参数说明:

**task_id**: 要终止的任务ID

**main_task**: 是否为主任务(只需在cpu密集型线性任务中填写)

返回值: 布尔值，表示终止是否成功

### 使用示例:

```
import time
from task_scheduling.variable import *
from task_scheduling.utils import interruptible_sleep


def infinite_task():
    while True:
        interruptible_sleep(1)
        print("running...")
        

if __name__ == "__main__":
    from task_scheduling.scheduler import io_liner_task
    from task_scheduling.task_creation import task_creation, shutdown

    task_id = task_creation(
        None, None, scheduler_io, True, "infinite_task",
        infinite_task, priority_low
    )
    time.sleep(3)
    io_liner_task.force_stop_task(task_id)  

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(True)
```

- task_scheduler.add_ban_task_name(task_name: str) -> None:

- task_scheduler.remove_ban_task_name(task_name: str) -> None:

添加和删除禁用任务名称。已添加的任务会被阻止运行

参数说明:

**task_name**:函数名字

### 使用示例:

```
import time


def line_task(input_info):
    while True:
        time.sleep(1)
        print(input_info)


input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown, task_scheduler
    from task_scheduling.variable import *

    task_id1 = task_creation(None,
                             None,
                             scheduler_io,
                             True,
                             "task1",
                             line_task,
                             priority_low,
                             input_info)

    task_scheduler.add_ban_task_name("task1")

    task_id2 = task_creation(None,
                             None,
                             scheduler_io,
                             True,
                             "task1",
                             line_task,
                             input_info)

    task_scheduler.remove_ban_task_name("task1")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        shutdown(True)
```

- cancel_the_queue_task_by_name(self, task_name: str) -> None:

取消队列中的某类任务

参数说明:

**task_name**:函数名字

### 使用示例:

```
import time


def line_task(input_info):
    while True:
        time.sleep(1)
        print(input_info)


input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown, task_scheduler
    from task_scheduling.variable import *

    task_id1 = task_creation(None,
                             None,
                             scheduler_io,
                             True,
                             "task1",
                             line_task,
                             priority_low,
                             input_info)

    task_scheduler.cancel_the_queue_task_by_name("task1")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(True)
```

- shutdown(force_cleanup: bool) -> None:

关闭调度器，必要代码在关闭时必须运行

参数说明:

**force_cleanup**:是否等待剩下任务运行

### 使用示例:

```
from task_scheduling.task_creation import shutdown
shutdown(True)
```

- update_config(key: str, value: Any) -> Any:

临时更新配置文件中参数,请放在`if __name__ == "__main__":`前面

参数说明:

**key**: 键

**value**: 值

返回值:True或者报错信息

### 使用示例:

```
from task_scheduling import update_config
update_config(key, value)
if __name__ == "__main__":
    ...
```

## 线程级任务管理(实验性功能)

!!!该功能只支持CPU密集型线性任务!!!

当配置文件中`thread_management=True`,开启该功能`线程级任务管理(实验性功能)`默认为关闭状态

`main_task`中前三位接受参数必须为`share_info`, `_sharedtaskdict`, `task_signal_transmission`

`@wait_branch_thread_ended`必须放在main_task上面，防止主线程结束,分支线程还没运行完导致错误

`other_task`为需要运行的分支线程,上面必须添加`@branch_thread_control`装饰器来控制和监视

`@branch_thread_control`装饰器接收参数`share_info`, `_sharedtaskdict`, `timeout_processing`, `task_name`

`task_name`必须是唯一不重复的,用于获取其他分支线程的task_id(使用`_sharedtaskdict.read(task_name)`获取task_id去终止，暂停或恢复)

使用`threading.Thread`语句必须添加`daemon=True`将线程设置为守护线程(没有添加会让关闭操作时间增加,反正主线程结束,会强制终止所有分支线程)

所有的分支线程都可以在网页端查看到运行状态(开启网页端请使用`start_task_status_ui()`)

这里提供两个控制函数:

在主线程内使用`task_signal_transmission.put((_sharedtaskdict.read(task_name), "action"))` action可以填写为`kill`,
`pause`, `resume`

在主线程外部可以使用`cpu_liner_task.force_stop_task()`等上面介绍的api

`cpu_liner_task.force_stop_task()`较为特殊,在`cpu_liner_task`调度器中还要接受一个布尔参数,设置为`False`
才能跳过检测去关闭分支线程`

### 使用示例:

```
import threading
import time
from task_scheduling.utils import wait_branch_thread_ended, branch_thread_control


@wait_branch_thread_ended
def main_task(share_info, _sharedtaskdict, task_signal_transmission, input_info):
    task_name = "other_task"
    timeout_processing = True

    @branch_thread_control(share_info, _sharedtaskdict, timeout_processing, task_name)
    def other_task(input_info):
        while True:
            time.sleep(1)
            print(input_info)

    threading.Thread(target=other_task, args=(input_info,), daemon=True).start()

    # Use this statement to terminate the branch thread
    # time.sleep(4)
    # task_signal_transmission.put((_sharedtaskdict.read(task_name), "kill"))


from task_scheduling.config import update_config
update_config("thread_management", True)

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown
    from task_scheduling.task_info import start_task_status_ui
    from task_scheduling.variable import *

    start_task_status_ui()

    task_id1 = task_creation(
        None, None, scheduler_cpu, True, "linear_task",
        main_task, priority_low, "test")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(True)
```

## 配置

文件存储在:`task_scheduling/config/config.yaml`

同一类型的 CPU 优化异步任务可以运行的最大数量

`cpu_asyncio_task: 8`

IO 密集型异步任务中相同类型任务的最大数量

`io_asyncio_task: 20`

可以运行的相同类型的面向 CPU 的线性任务的最大数量

`cpu_liner_task: 20`

I-O 密集型线性任务中相同类型任务的最大数量

`io_liner_task: 20`

定时器执行最多的任务

`timer_task: 30`

当长时间没有任务时，关闭任务调度器（秒）

`max_idle_time: 60`

当一个任务运行很长时间而未完成时，它会被强制结束（秒）

`watch_dog_time: 80`

任务状态中可以存储的最大记录数

`maximum_task_info_storage: 20`

检查任务状态是否正确需要多少秒，建议使用较长的时间间隔（秒）

`status_check_interval: 800`

是否在进程中启用线程管理

`thread_management: False`

是否应该抛出异常以便定位错误

`exception_thrown: False`

### 如果你有更好的想法，欢迎提交一个 PR

## 参考库：

为了便于后续修改,有些文件是直接放入文件夹,而不是通过 pip
安装的,所以这里明确说明了使用的库:https://github.com/glenfant/stopit