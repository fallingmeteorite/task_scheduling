- [English version](https://github.com/fallingmeteorite/task_scheduling/blob/main/README.md)
- [中文版本](https://github.com/fallingmeteorite/task_scheduling/blob/main/README_CN.md)

# Task Scheduling Library

A powerful Python task scheduling library that supports both asynchronous and synchronous task execution, providing
robust task management and monitoring features (with `NO GIL` already supported)

## Core Features

- Task Scheduling: Supports both asynchronous and synchronous code, tasks with the same name are automatically queued
  for execution
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
- Dependent Task Execution (Experimental Feature): Functions that rely on the results returned by the main task will be
  triggered and executed.
- Task Retry: Retry running the task when the corresponding error occurs

## Future plans

Not available at the moment

## Installation

```commandline
pip install --upgrade task_scheduling
```

## Running from the Command Line

### !!!Warning!!!

Does not support precise control over tasks

### Example of Use:

```commandline
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

You can use it with Python version 3.14 or above by enabling `NO GIL`. During runtime, it will output
`Free threaded is enabled`.

Run the following example to see the speed difference between the `GIL` and `NO GIL` versions

### Example of Use:

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
        task_scheduler.shutdown_scheduler()
```

## Change Log Level

### !!!Warning!!!

Please place it before `if __name__ == "__main__":`

### Example of Use:

```python
from task_scheduling.common import set_log_level

set_log_level("DEBUG")  # INFO, DEBUG, ERROR, WARNING

if __name__ == "__main__":
    ...
```

## Open Monitoring Page

The web interface allows you to view task status and runtime, and you can pause, terminate, or resume tasks.

### Example of Use:

```python
from task_scheduling.webui import start_task_status_ui

# Launch the web interface and visit: http://localhost:8000
start_task_status_ui()
```

## Create Task

- task_creation(delay: int or None, daily_time: str or None, function_type: str, timeout_processing: bool, task_name:
  str, func: Callable, *args, **kwargs) -> str or None:

### Parameter Description:

**delay**: Delay execution time (seconds), used for scheduled tasks (fill in None if not used)

**daily_time**: Daily execution time, format "HH:MM", used for scheduled tasks (do not use None)

**function_type**: Function types (`FUNCTION_TYPE_IO`, `FUNCTION_TYPE_CPU`, `FUNCTION_TYPE_TIMER`)

**timeout_processing**: Whether to enable timeout detection and forced termination (`True`, `False`)

**task_name**: Task name; tasks with the same name will be executed in queue

**func**: Function to be executed

**priority**: Task Priority (`priority_low`, `priority_high`)

**args, kwargs**: Function parameters

Return value: Task ID string

### Example of Use:

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
        task_scheduler.shutdown_scheduler()

```

## Task Retry

- retry_on_error(exceptions: Union[Type[Exception], Tuple[Type[Exception], ...], None], max_attempts: int, delay:
  Union[float, int]) -> Any:

### Parameter Description:

**exceptions**: When should retries start based on the type of error?

**max_attempts**: Maximum number of attempts

**delay**: Interval time between each retry

### Usage example:

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

## Pause or Resume Task Execution

- pause_api(task_type: str, task_id: str) -> bool:

- resume_api(task_type: str, task_id: str) -> bool:

### !!!Warning!!!

When a task is paused, the timeout timer still operates. If you need to use the pause function, it is recommended to
disable the timeout handling to prevent the task from being terminated due to a timeout when it resumes.

### Parameter Description:

**task_type**: The scheduler where the task is located (`CPU_ASYNCIO`, `IO_ASYNCIO`, `CPU_LINER`, `IO_LINER`, `TIMER`)

**task_id**: The ID of the task to be controlled

Return value: Boolean, indicating whether the operation was successful

### Example of Use:

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
        task_scheduler.shutdown_scheduler()
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

```python
from task_scheduling.mark import task_function_type
from task_scheduling.variable import *

task_function_type.append_to_dict("CPU_Task", FUNCTION_TYPE_CPU)
print(task_function_type.read_from_dict("CPU_Task"))
```

## Get Task Results

- get_result_api(task_type: str, task_id: str) -> Any:

### Function Description

Return value: The result of the task, or None if not completed

### Parameter Description:

**task_type**: Task Type

**task_id**: Task ID

### Example of Use:

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
        task_scheduler.shutdown_scheduler()
```

## Get All Task Statuses

- get_tasks_info() -> str:

### Parameter Description:

Return value: a string containing the task status

### Example of Use:

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
        task_scheduler.shutdown_scheduler()
```

## Get Specific Task Status

- get_task_status(self, task_id: str) -> Optional[Dict[str, Optional[Union[str, float, bool]]]]:

### Parameter Description:

**task_id**: Task ID

Return value: A dictionary containing the task status

### Example Usage:

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
        task_scheduler.shutdown_scheduler()
```

# Get total number of tasks

- get_task_count(self, task_name) -> int:

- get_all_task_count(self) -> Dict[str, int]:

### Parameter Description:

**task_name**: Function Name

Return value: dictionary or integer

### Example of Use:

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
        task_scheduler.shutdown_scheduler()
```

## Forcefully terminate the running task.

- kill_api(task_type: str, task_id: str) -> bool

### !!!Warning!!!

The code does not support terminating blocking tasks. An alternative version is provided for `time.sleep`. For long
waits, please use `interruptible_sleep`, and for asynchronous code, use `await asyncio.sleep`.

### Parameter Description:

**task_type**: Task Type

**task_id**: ID of the task to be terminated

Return value: Boolean, indicating whether the termination was successful

### Example of Use:

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
        task_scheduler.shutdown_scheduler()
```

## Add or Remove Disabled Task Names

- task_scheduler.add_ban_task_name(task_name: str) -> None:

- task_scheduler.remove_ban_task_name(task_name: str) -> None:

### Function Description

After adding the name of a certain type of task, this type of task will be intercepted and prevented from running.

### Parameter Description:

**task_name**: Function Name

### Example of Use:

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
        task_scheduler.shutdown_scheduler()
```

## Cancel a Certain Type of Task in the Queue

- cancel_the_queue_task_by_name(self, task_name: str) -> None:

### Parameter Description:

**task_name**: Function Name

### Example of Use:

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
        task_scheduler.shutdown_scheduler()
```

## Shut Down the Scheduler

- shutdown_scheduler() -> None:

### !!!Warning!!!

This function must be executed before shutting down to terminate and clean up the running tasks.

### Example Usage:

```python
from task_scheduling.manager import task_scheduler

task_scheduler.shutdown_scheduler()
```

## Temporary Update of Configuration File Parameters (Hot Reload)

- update_config(key: str, value: Any) -> Any:

### !!!WARNING!!!

Please place it before `if __name__ == "__main__":`,some parameters cannot be modified after startup and take effect

### Parameter Description:

**key**: key

**value**: value

Return value: True or an error message

### Example Usage:

```python
from task_scheduling.common import update_config

key, value = None
update_config(key, value)
if __name__ == "__main__":
    ...
```

## Thread-Level Task Management (Experimental Feature)

### !!!Warning!!!

!!!This feature only supports CPU-intensive linear tasks!!!

### Function Description:

In `main_task`, the first three parameters must be `share_info`, `_sharedtaskdict`, and `task_signal_transmission`.(If
this feature is enabled, normal tasks can also be used, you just need not to provide the three parameters mentioned
above)

`@wait_branch_thread_ended` must be placed above the main_task to prevent errors caused by the main thread ending before
the branch thread has finished running.

`other_task` is the branch thread that needs to run, and the `@branch_thread_control` decorator must be added above it
to control and monitor it.

The `@branch_thread_control` decorator accepts the parameters `share_info`, `_sharedtaskdict`, `timeout_processing`, and
`task_name`.

`task_name` must be unique and not duplicated, used to obtain the task_id of other branch threads (use
`_sharedtaskdict.read(task_name)` to get the task_id for terminating, pausing, or resuming them)

When using `threading.Thread`, you must add `daemon=True` to set the thread as a daemon thread (if not added, closing
operations will take longer; anyway, once the main thread ends, it will forcibly terminate all child threads).

All branch threads can have their running status viewed on the web interface (to open the web interface, please use
`start_task_status_ui()`)

Here are two control functions:

Using `task_signal_transmission[_sharedtaskdict.read(task_name)] = ["action"]` in the main thread you can fill in
`kill`, `pause`,
`resume`, you can also fill in several operations in order

`kill_api()` can be used outside the main thread

### Example of Use:

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
        task_scheduler.shutdown_scheduler()
```

## Task Tree Mode Management (Experimental Feature)

### Function Description

The task names in the dictionary will be displayed as `task_group_name|task_name`. When a task named `task_group_name`
is terminated, all tasks displayed as `task_group_name|task_name` will also be terminated together.

### Parameter Description

**task_group_name**: The name of the main task in this task tree (the task itself is just a carrier), all sub-tasks will
include the name of this main task

**task_dict**: The `key` stores the task name, the `value` stores the function to be executed, whether to enable timeout
detection and forced termination (`True`, `False`), and the parameters required by the function (must follow the order)

### Example of Use:

```python
import time


def liner_task(input_info):
    while True:
        time.sleep(1)
        print(input_info)


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
        task_scheduler.shutdown_scheduler()
```

## Dependent Task Execution (Experimental Feature)

- task_dependency_manager(main_task_id: str, dependent_task: Callable, *args) -> None:

### !!!Warning!!!

If the main task needs to return parameters, they must be in tuple format; other formats are not accepted.

### Function Description

After creating the main task using `task_creation`, use the `task_dependency_manager` class to set functions that run
depending on the result returned by the main task. The class methods include `after_completion`: runs after the main
task is completed (return value not required), `after_cancel`: runs after the main task is canceled, `after_timeout`:
runs after the main task times out, `after_error`: runs after the main task encounters an error.

`main_task_id` should be filled in with the task id of the main task returned by task_creation

`dependent_task` specifies the dependent task to be executed.

The following are the parameters required by dependent tasks. The parameters returned by the main task are at the end,
and the first six digits before the dependent task parameters should be filled in as

The six parameters required for `task_creation`:

**delay**: Delay execution time (seconds), used for scheduled tasks (fill in None if not used)

**daily_time**: Daily execution time, format "HH:MM", used for scheduled tasks (do not use None)

**function_type**: Function types (`FUNCTION_TYPE_IO`, `FUNCTION_TYPE_CPU`, `FUNCTION_TYPE_TIMER`)

**timeout_processing**: Whether to enable timeout detection and forced termination (`True`, `False`)

**task_name**: Task name; tasks with the same name will be executed in queue

**priority**: Task Priority (`priority_low`, `priority_high`)

### Parameter Description

**main_task_id**: The task ID of the main task

**dependent_task**: The dependent task to run

**args**: Parameters required by the dependent task; the parameters returned by the main task are at the end.

### Example of Use:

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
        task_scheduler.shutdown_scheduler()
```

## Web control terminal

![01.png](https://github.com/fallingmeteorite/task_scheduling/blob/main/img/01.png)

Task status UI available at http://localhost:8000

- Monitor task status and control tasks (`Terminate`, `Pause`, `Resume`)

## Configuration

The file is stored in: `task_scheduling/config/config_gil.yaml or config_no_gil.yaml`

## !!!Warning!!!

`no_gil` and `gil` have differences in `io_liner_task` and `timer_task`

The maximum number of CPU-intensive asynchronous tasks with the same name that can run

`cpu_asyncio_task: 30`

Maximum Number of IO-Intensive Asynchronous Tasks

`io_asyncio_task: 40`

Maximum number of tasks running in CPU-intensive linear tasks

`cpu_liner_task: 30`

Maximum number of tasks running in IO-intensive linear tasks

`io_liner_task: 1000` `no_gil: 60`

Maximum number of tasks executed by the timer

`timer_task: 1000` `no_gil: 60`

Time to wait without tasks before shutting down the task scheduler (seconds)

`max_idle_time: 300`

Force stop if the task runs for too long without completion (seconds)

`watch_dog_time: 300`

Maximum number of tasks stored in the task status memory

`maximum_task_info_storage: 2000`

How often to check if the task status in memory is correct (seconds)

`status_check_interval: 300`

Maximum number of returned results that a single scheduler can store

`maximum_result_storage: 2000`,

How often to clear the return result storage (seconds)

`maximum_result_time_storage: 300`,

Should an exception be thrown without being caught in order to locate the error?

`exception_thrown: False`

### If you have a better idea, feel free to submit a PR.

## Reference library:

For the convenience of later modifications, some files are placed directly in the folder instead of being installed via
pip, so the libraries used are explicitly stated here: https://github.com/glenfant/stopit