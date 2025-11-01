- [English version](./README.md)
- [中文版本](./README_CN.md)

# Task Scheduling Library

一个功能强大的Python任务调度库,支持异步和同步任务执行,提供强大的任务管理和监控功能(已支持`NO GIL`)

## Core Features

- Task Scheduling: Supports both asynchronous and synchronous code, tasks with the same name are automatically queued for execution
- Task Management: Powerful task status monitoring and management capabilities
- Flexible control: Supports sending (terminate, pause, resume) commands to the executing code
- Timeout Handling: Timeout detection can be enabled for tasks, and long-running tasks will be forcibly terminated
- Status Check: Retrieve the current task status directly through the interface or the web control panel
- Intelligent sleep: Automatically enters sleep mode when idle to save resources
- Priority Management: When there are too many tasks, high-priority tasks will be executed first
- Result Retrieval: Allows obtaining the execution results returned by the task
- Task Disable Management: You can add task names to the blacklist, and adding tasks with these names will be blocked
- Queue task cancellation: You can cancel all queued tasks with the same name
- Thread-level task management (experimental feature): Flexible task structure management
- Task tree mode management (experimental feature): When the main task ends, all other branch tasks will be terminated

## Installation

```
pip install --upgrade task_scheduling
```

## Running from the Command Line

### !!!Warning!!!

Does not support precise control over tasks

### Example of Use:

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

Use `ctrl c` to exit the program

# Detailed Explanation of Core APIs

### Support for `NO GIL`

You can use it with Python version 3.14 or above by enabling `NO GIL`. During runtime, it will output `Free threaded is enabled`.

Run the following example to see the speed difference between the `GIL` and `NO GIL` versions

### Example of Use:

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

## Change Log Level

### !!!Warning!!!

Please place it before `if __name__ == "__main__":`

### Example of Use:

```
from task_scheduling.common import set_log_level

set_log_level("DEBUG") # INFO, DEBUG, ERROR, WARNING

if __name__ == "__main__":
    ......
```

## Open Monitoring Page

The web interface allows you to view task status and runtime, and you can pause, terminate, or resume tasks.

### Example of Use:

```
from task_scheduling.web_ui import start_task_status_ui

# Launch the web interface and visit: http://localhost:8000
start_task_status_ui()
```

## Create Task

- task_creation(delay: int or None, daily_time: str or None, function_type: str, timeout_processing: bool, task_name:
  str, func: Callable, *args, **kwargs) -> str or None:

### Parameter Description:

**delay**: Delay execution time (seconds), used for scheduled tasks (fill in None if not used)

**daily_time**: Daily execution time, format "HH:MM", used for scheduled tasks (do not use None)

**function_type**: Function types (`scheduler_io`, `scheduler_cpu`, `scheduler_timer`)

**timeout_processing**: Whether to enable timeout detection and forced termination (`True`, `False`)

**task_name**: Task name; tasks with the same name will be executed in queue

**func**: Function to be executed

**priority**: Task Priority (`priority_low`, `priority_high`)

**args, kwargs**: Function parameters

Return value: Task ID string

### Example of Use:

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

## Pause or Resume Task Execution

- pause_and_resume_task(self, task_id: str, action: str) -> bool:

### !!!Warning!!!

When a task is paused, the timeout timer still operates. If you need to use the pause function, it is recommended to disable the timeout handling to prevent the task from being terminated due to a timeout when it resumes.

### Parameter Description:

**task_id**: The ID of the task to be controlled

**action**: (can be filled in with `pause`, `resume`)

Return value: Boolean, indicating whether the operation was successful

### Example of Use:

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

## Function Type Checking

- FunctionRunner(self, func: Callable, task_name: str, *args, **kwargs) -> None:

### Function Description

Check the function type and save it to a file (there are two types in total: `scheduler_cpu`, `scheduler_io`)

### Parameter Description:

**func**: Function to be tested

**task_name**: Function Name

*args, **kwargs: Function parameters

### Example of Use:

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

## Reading Function Types

- task_function_type.append_to_dict(task_name: str, function_type: str) -> None:

- task_function_type.read_from_dict(task_name: str) -> Optional[str]:

### Function Description

Read the type of the stored function or write it; the storage file is: `task_scheduling/function_data/task_type.pkl`

### Parameter Description:

**task_name**: Function Name

**function_type**: The type of function to write (can be filled in as `scheduler_cpu` or `scheduler_io`)

*args, **kwargs: Function parameters

### Example of Use:

```
from task_scheduling.check task_function_type
from task_scheduling.variable import *

task_function_type.append_to_dict("CPU_Task", scheduler_cpu)
print(task_function_type.read_from_dict("CPU_Task"))

```

## Get Task Results

- get_task_result(task_id: str) -> Optional[Any]:

### Function Description

Return value: The result of the task, or None if not completed

### Parameter Description:

**task_id**: Task ID

### Example of Use:

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

## Get All Task Statuses

- get_tasks_info() -> str:

### Parameter Description:

Return value: a string containing the task status

### Example of Use:

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

## Get Specific Task Status

- get_task_status(self, task_id: str) -> Optional[Dict[str, Optional[Union[str, float, bool]]]]:

### Parameter Description:

**task_id**: Task ID

Return value: A dictionary containing the task status

### Example Usage:

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

# Get total number of tasks

- get_task_count(self, task_name) -> int:

- get_all_task_count(self) -> Dict[str, int]:

### Parameter Description:

**task_name**: Function Name

Return value: dictionary or integer

### Example of Use:

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

    task_id1 = task_creation(None, None, scheduler_io, True, "task1", line_task, priority_low, input_info)

    print(task_status_manager.get_task_count("task1"))
    print(task_status_manager.get_all_task_count())

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(True)
```

## Forcefully terminate the running task.

- force_stop_task(task_id: str) -> bool:

### !!!Warning!!!

The code does not support terminating blocking tasks. An alternative version is provided for `time.sleep`. For long waits, please use `interruptible_sleep`, and for asynchronous code, use `await asyncio.sleep`.

### Parameter Description:

**task_id**: ID of the task to be terminated

Return value: Boolean, indicating whether the termination was successful

### Example of Use:

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

## Add or Remove Disabled Task Names

- task_scheduler.add_ban_task_name(task_name: str) -> None:

- task_scheduler.remove_ban_task_name(task_name: str) -> None:

### Function Description

After adding the name of a certain type of task, this type of task will be intercepted and prevented from running.

### Parameter Description:

**task_name**: Function Name

### Example of Use:

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

    task_id1 = task_creation(None, None, scheduler_io, True, "task1", line_task, priority_low, input_info)

    task_scheduler.add_ban_task_name("task1")

    task_id2 = task_creation(None, None, scheduler_io, True, "task1", line_task, input_info)

    task_scheduler.remove_ban_task_name("task1")
    
    task_id3 = task_creation(None, None, scheduler_io, True, "task1", line_task, input_info)

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        shutdown(True)
```

## Cancel a Certain Type of Task in the Queue

- cancel_the_queue_task_by_name(self, task_name: str) -> None:

### Parameter Description:

**task_name**: Function Name

### Example of Use:

```
import time


def line_task(input_info):
    for i in range(5):
        time.sleep(1)
        print(input_info)


input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown, task_scheduler
    from task_scheduling.variable import *

    task_id1 = task_creation(None, None, scheduler_io, True, "task1", line_task, priority_low, input_info)
    task_id2 = task_creation(None, None, scheduler_io, True, "task1", line_task, priority_low, input_info)
    time.sleep(1)

    task_scheduler.cancel_the_queue_task_by_name("task1")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(True)
```

## Shut Down the Scheduler

- shutdown(force_cleanup: bool) -> None:

### !!!Warning!!!

This function must be executed before shutting down to terminate and clean up the running tasks.

### Example Usage:

**force_cleanup**: Whether to wait for remaining tasks to complete

### Example Usage:

```
from task_scheduling.task_creation import shutdown
shutdown(True)
```

## Temporary Update of Configuration File Parameters

- update_config(key: str, value: Any) -> Any:

### !!!WARNING!!!

Please place it before `if __name__ == "__main__":`

### Parameter Description:

**key**: key

**value**: value

Return value: True or an error message

### Example Usage:

```
from task_scheduling import update_config
update_config(key, value)
if __name__ == "__main__":
    ...
```

## Thread-Level Task Management (Experimental Feature)

### !!!Warning!!!

!!!This feature only supports CPU-intensive linear tasks!!!

### Function Description:

`Thread-level task management (experimental feature)` is disabled by default. You can enable this feature by setting `thread_management=True` in the configuration file.

In `main_task`, the first three parameters must be `share_info`, `_sharedtaskdict`, and `task_signal_transmission`.

`@wait_branch_thread_ended` must be placed above the main_task to prevent errors caused by the main thread ending before the branch thread has finished running.

`other_task` is the branch thread that needs to run, and the `@branch_thread_control` decorator must be added above it to control and monitor it.

The `@branch_thread_control` decorator accepts the parameters `share_info`, `_sharedtaskdict`, `timeout_processing`, and `task_name`.

`task_name` must be unique and not duplicated, used to obtain the task_id of other branch threads (use `_sharedtaskdict.read(task_name)` to get the task_id for terminating, pausing, or resuming them)

When using `threading.Thread`, you must add `daemon=True` to set the thread as a daemon thread (if not added, closing operations will take longer; anyway, once the main thread ends, it will forcibly terminate all child threads).

All branch threads can have their running status viewed on the web interface (to open the web interface, please use `start_task_status_ui()`)

Here are two control functions:

Using `task_signal_transmission[_sharedtaskdict.read(task_name)] = ["action"]` in the main thread you can fill in `kill`, `pause`,
`resume`, you can also fill in several operations in order

`force_stop_task()` can be used outside the main thread

### Example of Use:

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

## Task Tree Mode Management (Experimental Feature)

## Function Description

The task names in the dictionary will be displayed as `task_group_name|task_name`. When a task named `task_group_name` is terminated, all tasks displayed as `task_group_name|task_name` will also be terminated together.

### Parameter Description

**task_group_name**: The name of the main task in this task tree (the task itself is just a carrier), all sub-tasks will include the name of this main task

**task_dict**: The `key` stores the task name, the `value` stores the function to be executed, whether to enable timeout detection and forced termination (`True`, `False`), and the parameters required by the function (must follow the order)

### 使用示例:

```
import time

from task_scheduling.config import update_config


def liner_task(input_info):
    while True:
        time.sleep(1)
        print(input_info)


update_config("thread_management", True)
if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown
    from task_scheduling.utils import task_group
    from task_scheduling.web_ui import start_task_status_ui
    from task_scheduling.variable import *

    start_task_status_ui()

    task_group_name = "main_task"

    task_dict = {
        "task1": (liner_task, True, 1111),
        "task2": (liner_task, True, 2222),
        "task3": (liner_task, True, 3333),
    }

    task_id1 = task_creation(
        None, None, scheduler_cpu, True, task_group_name,
        task_group, priority_low, task_group_name, task_dict)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(True)
```

## Web control terminal

![01.png](https://github.com/fallingmeteorite/task_scheduling/blob/main/img/01.png)

Task status UI available at http://localhost:8000

- Monitor task status and control tasks (`Terminate`, `Pause`, `Resume`)

## Configuration

The file is stored in: `task_scheduling/config/config.yaml`

The maximum number of CPU-intensive asynchronous tasks with the same name that can run

`cpu_asyncio_task: 8`

Maximum Number of IO-Intensive Asynchronous Tasks

`io_asyncio_task: 20`

Maximum number of tasks running in CPU-intensive linear tasks

`cpu_liner_task: 20`

Maximum number of tasks running in IO-intensive linear tasks

`io_liner_task: 20`

Maximum number of tasks executed by the timer

`timer_task: 20`

Time to wait without tasks before shutting down the task scheduler (seconds)

`max_idle_time: 600`

Force stop if the task runs for too long without completion (seconds)

`watch_dog_time: 120`

Maximum number of tasks stored in the task status memory

`maximum_task_info_storage: 40`

How often to check if the task status in memory is correct (seconds)

`status_check_interval: 800`

Whether to enable hyper-threading management in CPU-intensive linear tasks

`thread_management: False`

Should an exception be thrown without being caught in order to locate the error?

`exception_thrown: False`

### If you have a better idea, feel free to submit a PR.

## Reference library:

For the convenience of later modifications, some files are placed directly in the folder instead of being installed via pip, so the libraries used are explicitly stated here: https://github.com/glenfant/stopit