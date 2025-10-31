- [English version](https://github.com/fallingmeteorite/task_scheduling/blob/main/README.md)
- [中文版本](https://github.com/fallingmeteorite/task_scheduling/blob/main/README_CN.md)

# Task Scheduling Library

A powerful Python task scheduling library that supports asynchronous and synchronous task execution, providing robust
task management and monitoring capabilities.(Supports `NO GIL`)

## Features

### Core Features

- Task scheduling: Supports asynchronous and synchronous code, with tasks of the same type automatically queued for
  execution

- Task Management: Powerful task status monitoring and management capabilities
- Flexible termination: Supports sending termination commands to executing code
- Timeout Handling: You can enable timeout detection for tasks, and long-running tasks will be forcibly terminated.
- Status Inquiry: Directly obtain the current status of the task through the interface (completed, error, timeout, etc.)
- Intelligent Sleep: Automatically enters sleep mode when idle to save resources

### Advanced Features

- Task priority management (low priority / high priority)
- Task pause and resume
- Task result retrieval
- Blocked task management
- Queue task cancellation
- Thread-level task management (experimental feature)

### Warning

- The code cannot terminate blocking tasks, such as write operations or network requests. Be sure to add corresponding
  logic, such as timeout interruption. For computational tasks and other tasks, termination is possible as long as the
  code is still running and not blocked (That is, the code continues to run without waiting and can terminate
  immediately.).
- For `time.sleep`, the library provides an alternative version. Use `interruptible_sleep` for long waits, and use await
  `asyncio.sleep` for asynchronous code.
- If you need to check errors and find the error location, please set the log level to `set_log_level("DEBUG")` and set
  the configuration file `exception_thrown: True`.
- The functions introduced below are applicable to all four schedulers, and special functions will be specifically
  marked.
- Tasks with the same name will be executed in queue. If you want to avoid this, you can add a suffix to the passed `task_name`.

## Installation

```
pip install --upgrade task_scheduling
```

## Command Line Operation

!!!Does not support precise control over tasks.!!!

```
python -m task_scheduling

#  The task scheduler starts.
#  Wait for the task to be added.
#  Task status UI available at http://localhost:8000

# Add command: -cmd <command> -n <task_name>

-cmd 'python test.py' -n 'test'
#  Parameter: {'command': 'python test.py', 'name': 'test'}
#  Create a success. task ID: 7fc6a50c-46c1-4f71-b3c9-dfacec04f833
#  Wait for the task to be added.
```

Use `ctrl + c` to exit.

## Core API Details

- Support for `NO GIL`

You can use Python version 3.14 or above and enable the `NO GIL` setting. If `NO GIL` is enabled, it will output `Free threaded is enabled`.

Run the following example to see the speed difference between the `GIL` and `NO GIL` versions.

### Usage Examples:

```
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
    from task_scheduling.task_creation import task_creation, shutdown
    from task_scheduling.variable import *

    task_creation(
        None, None, scheduler_io, True, "task1",
        linear_task, priority_low, "task1"
    )

    task_creation(
        None, None, scheduler_io, True, "task2",
        linear_task, priority_low, "task2"
    )

    task_creation(
        None, None, scheduler_io, True, "task3",
        linear_task, priority_low, "task3"
    )

    task_creation(
        None, None, scheduler_io, True, "task4",
        linear_task, priority_low, "task4"
    )

    task_creation(
        None, None, scheduler_io, True, "task5",
        linear_task, priority_low, "task5"
    )

    task_creation(
        None, None, scheduler_io, True, "task6",
        linear_task, priority_low, "task6"
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(True)
```

- Change log level

Please place it before `if __name__ == "__main__":`

### Usage Examples:

```
from task_scheduling.common import set_log_level

set_log_level("DEBUG") # INFO, DEBUG, ERROR, WARNING

if __name__ == "__main__":
    ......
```

- Start monitoring page

```
from task_scheduling.web_ui import start_task_status_ui

# Launch the web interface and visit: http://localhost:8000
start_task_status_ui()
```

- task_creation(delay: int or None, daily_time: str or None, function_type: str, timeout_processing: bool, task_name:
  str, func: Callable, *args, **kwargs) -> str or None:

Create and schedule a task for execution.

Parameter Description:

**delay**: Delay execution time (seconds), used for scheduled tasks.

**daily_time**: Daily execution time, format "HH:MM", used for scheduled tasks.

**function_type**: Function type (scheduler_io, scheduler_cpu, scheduler_timer).

**timeout_processing**: Whether to enable timeout detection and forced termination (True, False).

**task_name**: Tasks with the same name will be queued for execution.

**func**: The function to execute.

**priority**: Task priority (priority_low, priority_high).

*args, **kwargs: Function arguments.

Return Value: Task ID string.

### Usage Example:

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

Pause or resume a running task.

Parameter Description:

**task_id**: The ID of the task to control.

**action**: (Can be `pause`, `resume`).

Return Value: Boolean indicating whether the operation was successful.

!!!During pause, the timeout timer is still running. If you need to use the pause function, it is recommended to disable the timeout handling!!!

### Usage Example:

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

Check the function type and record it (two types: `scheduler_cpu`, `scheduler_io`).

Parameter Description:

**func**: The function to check.

**task_name**: The function name.

*args, **kwargs: Function arguments.

### Usage Example:

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
    from task_scheduling.check import FunctionRunner

    cpu_runner = FunctionRunner(example_cpu_intensive_function, "CPU_Task", 10000, 2)
    cpu_runner.run()

    io_runner = FunctionRunner(example_io_intensive_function, "IO_Task")
    io_runner.run()
```

- task_function_type.append_to_dict(task_name: str, function_type: str) -> None:

- task_function_type.read_from_dict(task_name: str) -> Optional[str]:

Read the stored type of a function or write it. Storage file: `task_scheduling/function_data/task_type.pkl`

Parameter Description:

**task_name**: The function name.

**function_type**:The function type to write (can be `scheduler_cpu`, `scheduler_io`).

*args, **kwargs:Function arguments.

### Usage Example:

```
from task_scheduling.check task_function_type
from task_scheduling.variable import *

task_function_type.append_to_dict("CPU_Task", scheduler_cpu)
print(task_function_type.read_from_dict("CPU_Task"))

```

- get_task_result(task_id: str) -> Optional[Any]:

Get the return value of a completed task.

Parameter Description:

**task_id**: Task ID.

Return Value: The task result, or None if not completed.

### Usage Example:

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

Get information about all tasks.

Return Value: A formatted string containing task information.

### Usage Example:

```
import time
from task_scheduling.variable import *

if __name__ == "__main__":
    from task_scheduling.manager import get_tasks_info
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

Get detailed status information for a specific task.

Parameter Description:

- task_id: Task ID.

Return Value: A dictionary containing task status information.

### Usage Example:

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

Get the total count of tasks.

Parameter Description:

**task_name**: The function name.

Return Value: Dictionary or integer.

### Usage Example:

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

- force_stop_task(task_id: str) -> bool:

Forcefully terminate a running task.

Parameter Description:

**task_id**: The ID of the task to terminate.

Return Value: Boolean indicating whether the termination was successful.

### Usage Example:

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

Add and remove blocked task names. Added tasks will be prevented from running.

Parameter Description:

**task_name**: The function name.

### Usage Example:

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

Cancel queued tasks of a certain type.

Parameter Description:

**task_name**: The function name.

### Usage Example:

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

Shut down the scheduler. Necessary code must be run upon shutdown.

Parameter Description:

**force_cleanup**: Whether to wait for remaining tasks to finish.

### Usage Example:

```
from task_scheduling.task_creation import shutdown
shutdown(True)
```

- update_config(key: str, value: Any) -> Any:

Temporarily update parameters in the configuration file,Please place it before `if __name__ == "__main__":`

Parameter Description:

**key**: key

**value**: value

Return value: True or error information

### Usage Example:

```
from task_scheduling import update_config
update_config(key, value)
if __name__ == "__main__":
    ...
```

## 线程级任务管理(实验性功能)

!!!This feature only supports CPU-intensive linear tasks!!!

When `thread_management=True` is set in the configuration file, this feature `Thread-level Task Management (experimental feature)` is enabled. By default, it is turned off.

In `main_task`, the first three parameters must be `share_info`, `_sharedtaskdict`, and `task_signal_transmission`.

`@wait_branch_thread_ended` must be placed above the main_task to prevent errors caused by the main thread ending before the branch thread has finished running.

`other_task` is the branch thread that needs to run, and the `@branch_thread_control` decorator must be added above it to control and monitor it.

The `@branch_thread_control` decorator receives the parameters `share_info`, `_sharedtaskdict`, `timeout_processing`, and `task_name`.

`task_name` must be unique and not duplicated, used to obtain the task_id of other branch threads (use `_sharedtaskdict.read(task_name)` to get the task_id for termination, pause, or resume).

When using the `threading.Thread` statement, you must add `daemon=True` to set the thread as a daemon thread (not adding it will increase the shutdown time; anyway, when the main thread ends, all child threads will be forcibly terminated).

All branch threads' running status can be viewed on the web interface (to enable the web interface, please use `start_task_status_ui()`)

Here are two control functions:

In the main thread, using `task_signal_transmission[_sharedtaskdict.read(task_name)] = ["action"]`, the action can be set to `kill`, `pause`, `resume`, or you can specify several actions in sequence.

Outside the main thread, you can use APIs such as `cpu_liner_task.force_stop_task()` mentioned above.

### Usage Example:

```
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
    # task_signal_transmission[_sharedtaskdict.read(task_name)] = ["kill"]


from task_scheduling.config import update_config
update_config("thread_management", True)

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown
    from task_scheduling.web_ui import start_task_status_ui
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

## Web Control Panel
![01.png](https://github.com/fallingmeteorite/task_scheduling/blob/main/img/01.png)

Task status UI available at http://localhost:8000

- Monitor task execution status

- Can control tasks ('Terminate', 'Pause', 'Resume')

## Configuration

File location: `task_scheduling/config/config.yaml`

Maximum number of CPU-optimized asynchronous tasks of the same type that can run concurrently.

`cpu_asyncio_task: 8`

Maximum number of I/O-intensive asynchronous tasks of the same type.

`io_asyncio_task: 20`

Maximum number of CPU-oriented linear tasks of the same type that can run concurrently.

`cpu_liner_task: 20`

Maximum number of I/O-intensive linear tasks of the same type.

`io_liner_task: 20`

Maximum number of tasks for the timer to execute.

`timer_task: 30`

Shut down the task scheduler after being idle for a long time (seconds).

`max_idle_time: 60`

Forcefully terminate a task if it runs for a long time without completing (seconds).

`watch_dog_time: 80`

Maximum number of records that can be stored in the task status.

`maximum_task_info_storage: 20`

Interval (seconds) for checking if the task status is correct. A longer interval is recommended.

`status_check_interval: 800`

Whether to enable thread management in the process.

`thread_management: False`

Whether exceptions should be thrown to locate errors.

`exception_thrown: False`

### If you have a better idea, feel free to submit a PR

## Reference libraries:

For ease of subsequent modification, some files are directly placed in the folder instead of being installed via pip, so
the libraries used are explicitly stated here: https://github.com/glenfant/stopit