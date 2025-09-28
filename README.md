- [English version](./README.md)
- [中文版本](./README_CN.md)

# Task Scheduling Library

A powerful Python task scheduling library that supports asynchronous and synchronous task execution, providing robust
task management and monitoring capabilities.

## Features

### Core Features

- Task scheduling: Supports asynchronous and synchronous code, with tasks of the same type automatically queued for
  execution

- Task Management: Powerful task status monitoring and management capabilities
- Flexible termination: Supports sending termination commands to executing code
- Timeout Handling: You can enable timeout detection for tasks, and long-running tasks will be forcibly terminated.
- Disable List: Tasks that fail to run can be added to the disable list to prevent repeated execution.
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

### Usage Examples:

- Change log level

Please place it before all import statements.

```
from task_scheduling.common import set_log_level

set_log_level("DEBUG") # INFO, DEBUG, ERROR, WARNING

if __name__ == "__main__":
    ......
```

- Start monitoring page

```
from task_scheduling.task_info import start_task_status_ui

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

When `thread_management=True` is set in the configuration file, enabling this feature
`thread-level task management (experimental feature)`, this feature is turned off by default.

!!!This feature only supports CPU-intensive linear tasks!!!

The first three parameters accepted in `mian_task` must be `task_manager`, `_threadterminator`, and `StopException`.

In `other_task`, the first two parameters must accept `_threadterminator` and `StopException`.

`task_id` must be unique and not duplicated. It is used to terminate other branch threads under the main thread, and all
other branch threads must be closed before closing the main thread.

When using the `threading.Thread` statement, you must add `daemon=True` to set the thread as a daemon thread.

`cpu_liner_task.force_stop_task()` is quite special. In the `cpu_liner_task` scheduler, it also needs to accept a
boolean parameter, which must be set to `False` to skip the check and close the branch thread.

### Usage Example:

```
import threading
import time
from task_scheduling.utils import interruptible_sleep


def main_task(task_manager, _threadterminator, StopException, input_info):
    def other_task(_threadterminator, StopException, input_info):
        with _threadterminator.terminate_control() as terminate_ctx:
            try:
                task_id = 1001001
                task_manager.add(terminate_ctx, None, task_id)
                while True:
                    interruptible_sleep(1)
                    print(input_info)
            except StopException:
                pass

    threading.Thread(target=other_task, args=(_threadterminator, StopException, input_info,), daemon=True).start()

    while True:
        interruptible_sleep(1)
        print(2)

from task_scheduling.config import update_config

update_config("thread_management", True)
input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown
    from task_scheduling.variable import *
    from task_scheduling.scheduler import cpu_liner_task

    from task_scheduling.common import set_log_level


    set_log_level("DEBUG")


    task_id1 = task_creation(
        None, None, scheduler_cpu, True, "linear_task",
        main_task, priority_low, "test")
    time.sleep(3)
    cpu_liner_task.force_stop_task(1001001, False)

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
    from task_scheduling.task_data import FunctionRunner

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
from task_scheduling.task_data task_function_type
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

- force_stop_task(task_id: str, main_task: bool) -> bool:

Forcefully terminate a running task.

Parameter Description:

**task_id**: The ID of the task to terminate.

**main_task**: Whether it is the main task (only needs to be specified for CPU-intensive linear tasks).

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

Temporarily update parameters in the configuration file.

Parameter Description:

**key**: key

**value**: value

Return value: True or error information

### Usage Example:

```
from task_scheduling import update_config
update_config(key, value)
```

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