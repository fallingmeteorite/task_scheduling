## introduce:

This python library is mainly used for task scheduling,
for example, there are a bunch of tasks here, the same type of tasks must be queued for execution,
and the tasks need strong management and monitoring

Asynchronous code and normal code are now supported,
specifically with event loops for asynchronous code

## Scope of application

This task scheduling is suitable for:

1.Network Requests: Handling multiple HTTP requests concurrently, where each request can be scheduled and executed
asynchronously.

2.File I/O Operations: Reading from or writing to multiple files concurrently, especially when dealing with large files
or when the I/O operations are slow.

3.Database Queries: Executing multiple database queries concurrently, especially when the queries involve waiting for
database responses.

4.Web Scraping: Running multiple web scraping tasks concurrently, where each task involves fetching and processing web
pages.

5.Real-time Data Processing: Processing real-time data streams, where tasks need to be executed as soon as data is
available.

6.Background Tasks: Running background tasks that perform periodic operations, such as data aggregation, cleanup, or
monitoring.

7.CPU-intensive task execution.

8.Threads in new processes can be well managed.

9.With analysis function, it can analyze which scheduler the execution function conforms.

## Feature description

1.You can send a termination command to the execution code

2.You can enable timeout processing for a task, and terminate the task if it runs for too long

3.When a task fails to run, it can be added to the disabled list and will not be executed thereafter

4.You can directly obtain the current task status through the interface, such as executing: "completed, error, timeout"

5.Automatically hibernate when there are no tasks

## Installation

!!! WARNING: If I/O-intensive task is running in a series of blocking tasks such as time.sleep, the task cannot be
forced
terminated, it is recommended to use `interruptible_sleep` instead of `time.sleep` for long waits
So, use `await asyncio.sleep` for asynchronous tasks

CPU-intensive tasks do not need to be processed at all, and can be forced to end even if `time.sleep` is running

```
pip install --upgrade task_scheduling
```

# Function introduction

### Function: task_creation(delay: int or None, daily_time: str or None, function_type: str, timeout_processing: bool, task_name: str, func: Callable, *args, **kwargs) -> str or None:

The core function is used to create a task and submit it to the scheduler. Currently the scheduler has
`cpu_asyncio_task, cpu_liner_task, io_asyncio_task, io_liner_task, timer_task`

(The task is of the "io" type) I/O intensive tasks run in the threads of the main process.

```

import asyncio
import time

from task_scheduling.utils import interruptible_sleep


def line_task(input_info):
    while True:
        interruptible_sleep(1)
        print(input_info)


async def asyncio_task(input_info):
    while True:
        await asyncio.sleep(1)
        print(input_info)


input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown

    task_id1 = task_creation(None,
                             # This is how long the delay is executed (in seconds)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the daily_time is not required
                             None,
                             # This is to be performed at what point (24-hour clock)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the delay is not required
                             'io',
                             # Running function type, there are "io, cpu, timer"
                             True,
                             # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
                             "task1",
                             # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
                             line_task,
                             # The function to be executed, parameters should not be passed here
                             input_info
                             # Pass the parameters required by the function, no restrictions
                             )

    task_id2 = task_creation(None,
                             # This is how long the delay is executed (in seconds)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the daily_time is not required
                             None,
                             # This is to be performed at what point (24-hour clock)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the delay is not required
                             'io',
                             # Running function type, there are "io, cpu, timer"
                             True,
                             # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
                             "task2",
                             # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
                             asyncio_task,
                             # The function to be executed, parameters should not be passed here
                             input_info
                             # Pass the parameters required by the function, no restrictions
                             )

    print(task_id1, task_id2)
    # cf478b6e-5e02-49b8-9031-4adc6ff915c2, cf478b6e-5e02-49b8-9031-4adc6ff915c2

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        shutdown(True)

```

(The task is of the "timer" type) Timer tasks are all run in the threads of a process, and are committed to the thread
pool when the specified time is reached

```

import time


def line_task(input_info):
    print(input_info)


input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown

    task_id1 = task_creation(10,
                             # This is how long the delay is executed (in seconds)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the daily_time is not required
                             None,  # 14:00
                             # This is to be performed at what point (24-hour clock)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the delay is not required
                             'timer',
                             # Running function type, there are "io, cpu, timer"
                             True,
                             # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
                             "task1",
                             # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
                             line_task,
                             # The function to be executed, parameters should not be passed here
                             input_info
                             # Pass the parameters required by the function, no restrictions
                             )

    task_id2 = task_creation(None,
                             # This is how long the delay is executed (in seconds)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the daily_time is not required
                             "13:03",  # 13.03
                             # This is to be performed at what point (24-hour clock)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the delay is not required
                             'timer',
                             # Running function type, there are "io, cpu, timer"
                             True,
                             # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
                             "task2",
                             # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
                             line_task,
                             # The function to be executed, parameters should not be passed here
                             input_info
                             # Pass the parameters required by the function, no restrictions
                             )

    print(task_id1, task_id2)
    # cf478b6e-5e02-49b8-9031-4adc6ff915c2, cf478b6e-5e02-49b8-9031-4adc6ff915c2

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        shutdown(True)

```

(The task is of the "cpu" type)Each task is separate in a process.

This `task_manager` will end the process when there are no threads in the process, so that the process will be recycled

Threaded tasks can be created in this process, and the library provides `task_manager`
that will pass the configuration file `thread_management=True` to the main function
where a new threaded task is created and managed through the task manager, as shown in an example below

!!! WARNING: The method is still experimental and there is no guarantee that there will be no unknown problems

`thread_management=False`

```
import time

def line_task(input_info):
    while True:
        interruptible_sleep(1)
        print(input_info)


input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown
    from task_scheduling.scheduler import cpu_liner_task

    task_id1 = task_creation(None,
                             # This is how long the delay is executed (in seconds)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the daily_time is not required
                             None,
                             # This is to be performed at what point (24-hour clock)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the delay is not required
                             'cpu',
                             # Running function type, there are "io, cpu, timer"
                             True,
                             # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
                             "task1",
                             # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
                             line_task,
                             # The function to be executed, parameters should not be passed here
                             input_info
                             # Pass the parameters required by the function, no restrictions
                             )

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        shutdown(True)


```

`thread_management=True`

```
import time

from task_scheduling.stopit import skip_on_demand


def line_task(task_manager, input_info):

    with skip_on_demand() as skip_ctx:
        task_id = 1001001
        # Create your own thread and give a unique ID to the incoming task_manager
        task_manager.add(skip_ctx, task_id)


input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown
    from task_scheduling.scheduler import cpu_liner_task

    task_id1 = task_creation(None,
                             # This is how long the delay is executed (in seconds)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the daily_time is not required
                             None,
                             # This is to be performed at what point (24-hour clock)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the delay is not required
                             'cpu',
                             # Running function type, there are "io, cpu, timer"
                             True,
                             # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
                             "task1",
                             # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
                             line_task,
                             # The function to be executed, parameters should not be passed here
                             input_info
                             # Pass the parameters required by the function, no restrictions
                             )

    task_id = 1001001
    time.sleep(2.0)
    cpu_liner_task.force_stop_task(task_id)
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        shutdown(True)

```

### FunctionRunner(self, func: Callable, task_name: str, *args, **kwargs) -> None:

A task that detects what type of function is executed. The detected parameters are stored in a file and read directly at
the next time

!!! WARNING: If you use this function, the CPU usage may increase slightly

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
    from task_scheduling.utils import FunctionRunner

    cpu_runner = FunctionRunner(example_cpu_intensive_function, "CPU_Task", 10000, 2)
    cpu_runner.run()

    io_runner = FunctionRunner(example_io_intensive_function, "IO_Task")
    io_runner.run()

```

### task_function_type.append_to_dict(task_name: str, function_type: str) -> None:

### task_function_type.read_from_dict(task_name: str) -> Optional[str]:

Add a function type and a view type. Files are stored in:`task_scheduling/function_data/task_type.pkl`

```
if __name__ == "__main__":
    from task_scheduling.function_data import task_function_type

    task_function_type.append_to_dict("CPU_Task", "test")

    print(task_function_type.read_from_dict("CPU_Task"))
    print(task_function_type.read_from_dict("CPU_Task"))
```

### get_task_result(task_id: str) -> Optional[Any]:

Get the data returned by the task.

```

import asyncio
import time


def line_task(input_info):
    time.sleep(4)
    return input_info


async def asyncio_task(input_info):
    await asyncio.sleep(4)
    return input_info


input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown
    from task_scheduling.scheduler import io_liner_task

    task_id1 = task_creation(None,
                             # This is how long the delay is executed (in seconds)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the daily_time is not required
                             None,
                             # This is to be performed at what point (24-hour clock)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the delay is not required
                             'io',
                             # Running function type, there are "io, cpu, timer"
                             True,
                             # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
                             "task1",
                             # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
                             line_task,
                             # The function to be executed, parameters should not be passed here
                             input_info
                             # Pass the parameters required by the function, no restrictions
                             )

    while True:
        result = io_liner_task.get_task_result(task_id1)

        if result is not None:
            print(result)
            # test
            break
        else:
            time.sleep(0.1)

    shutdown(True)

```

### get_tasks_info() -> str:

Get information on all tasks. It is convenient to manage all tasks and move on to the next step

```
import asyncio
import time


def line_task(input_info):
    time.sleep(4)
    return input_info


async def asyncio_task(input_info):
    await asyncio.sleep(4)
    return input_info


input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown
    from task_scheduling.queue_info_display import get_tasks_info

    task_id1 = task_creation(5,
                             # This is how long the delay is executed (in seconds)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the daily_time is not required
                             None,
                             # This is to be performed at what point (24-hour clock)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the delay is not required
                             'timer',
                             # Running function type, there are "io, cpu, timer"
                             True,
                             # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
                             "task1",
                             # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
                             line_task,
                             # The function to be executed, parameters should not be passed here
                             input_info
                             # Pass the parameters required by the function, no restrictions
                             )

    try:
        while True:
            print(get_tasks_info())
            # tasks queue size: 1, running tasks count: 0, failed tasks count: 0
            # name: task1, id: 79185539-01e5-4576-8f10-70bb4f75374f, status: waiting, elapsed time: nan seconds
            time.sleep(2.0)
    except KeyboardInterrupt:
        shutdown(True)

```

### task_status_manager.get_task_status(self, task_id: str) -> Optional[Dict[str, Optional[Union[str, float, bool]]]]:

Get information about a single task. This will return a dictionary for easy user access

```
import asyncio
import time


def line_task(input_info):
    while True:
        time.sleep(1)
        print(input_info)


async def asyncio_task(input_info):
    while True:
        await asyncio.sleep(1)
        print(input_info)


input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown
    from task_scheduling.scheduler_management import task_status_manager

    task_id1 = task_creation(None,
                             # This is how long the delay is executed (in seconds)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the daily_time is not required
                             None,
                             # This is to be performed at what point (24-hour clock)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the delay is not required
                             'io',
                             # Running function type, there are "io, cpu, timer"
                             True,
                             # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
                             "task1",
                             # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
                             line_task,
                             # The function to be executed, parameters should not be passed here
                             input_info
                             # Pass the parameters required by the function, no restrictions
                             )

    print(task_status_manager.get_task_status(task_id1))
    # {'task_name': 'task1', 'status': 'waiting', 'start_time': None, 'end_time': None, 'error_info': None, 'is_timeout_enabled': True}
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        shutdown(True)

```

### get_task_count(self, task_name) -> int

### get_all_task_count(self) -> Dict[str, int]:

Gets the total presence of a task

```
import asyncio
import time


def line_task(input_info):
    while True:
        time.sleep(1)
        print(input_info)


async def asyncio_task(input_info):
    while True:
        await asyncio.sleep(1)
        print(input_info)


input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown
    from task_scheduling.scheduler_management import task_status_manager

    task_id1 = task_creation(None,
                             # This is how long the delay is executed (in seconds)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the daily_time is not required
                             None,
                             # This is to be performed at what point (24-hour clock)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the delay is not required
                             'io',
                             # Running function type, there are "io, cpu, timer"
                             True,
                             # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
                             "task1",
                             # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
                             line_task,
                             # The function to be executed, parameters should not be passed here
                             input_info
                             # Pass the parameters required by the function, no restrictions
                             )

    print(task_status_manager.get_task_count("task1"))
    # 1
    print(task_status_manager.get_all_task_count())
    # OrderedDict({'task1': 1})

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        shutdown(True)

```

### task_scheduler.add_ban_task_name(task_name: str) -> None:

### task_scheduler.remove_ban_task_name(task_name: str) -> None:

Add and remove disabled task names. After you add a disabled task name, the task cannot be added but is blocked

```
import asyncio
import time


def line_task(input_info):
    while True:
        time.sleep(1)
        print(input_info)


async def asyncio_task(input_info):
    while True:
        await asyncio.sleep(1)
        print(input_info)


input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown, task_scheduler

    task_id1 = task_creation(None,
                             # This is how long the delay is executed (in seconds)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the daily_time is not required
                             None,
                             # This is to be performed at what point (24-hour clock)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the delay is not required
                             'io',
                             # Running function type, there are "io, cpu, timer"
                             True,
                             # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
                             "task1",
                             # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
                             line_task,
                             # The function to be executed, parameters should not be passed here
                             input_info
                             # Pass the parameters required by the function, no restrictions
                             )

    task_scheduler.add_ban_task_name("task1")

    task_id2 = task_creation(None,
                             # This is how long the delay is executed (in seconds)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the daily_time is not required
                             None,
                             # This is to be performed at what point (24-hour clock)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the delay is not required
                             'io',
                             # Running function type, there are "io, cpu, timer"
                             True,
                             # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
                             "task1",
                             # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
                             line_task,
                             # The function to be executed, parameters should not be passed here
                             input_info
                             # Pass the parameters required by the function, no restrictions
                             )

    task_scheduler.remove_ban_task_name("task1")

    # Start running io linear task, task ID: 19a643f3-d8fd-462f-8f36-0eca7a447741
    # Task name 'task1' has been added to the ban list.
    # Task name 'task1' is banned, cannot add task, task ID: a4bc60b1-95d1-423d-8911-10f520ee88f5
    # Task name 'task1' has been removed from the ban list.
    try:
        while True:
            time.sleep(2.0)
    except KeyboardInterrupt:
        shutdown(True)

```

### task_scheduler.cancel_the_queue_task_by_name(self, task_name: str) -> None:

Cancel a task that is being queued. If the task has already started, the cleanup function does not take effect

```
import asyncio
import time


def line_task(input_info):
    while True:
        time.sleep(1)
        print(input_info)


async def asyncio_task(input_info):
    while True:
        await asyncio.sleep(1)
        print(input_info)


input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown, task_scheduler

    task_id1 = task_creation(None,
                             # This is how long the delay is executed (in seconds)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the daily_time is not required
                             None,
                             # This is to be performed at what point (24-hour clock)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the delay is not required
                             'io',
                             # Running function type, there are "io, cpu, timer"
                             True,
                             # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
                             "task1",
                             # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
                             line_task,
                             # The function to be executed, parameters should not be passed here
                             input_info
                             # Pass the parameters required by the function, no restrictions
                             )

    task_scheduler.cancel_the_queue_task_by_name("task1")

    # This type of name task has been removed

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        shutdown(True)

```

### force_stop_task(task_id: str) -> bool:

All 4 schedulers have this function for terminating a running task. Warning: If the function is executing a
process-blocking function such as `time.sleep`, it will have to wait for the execution to finish before terminating the
function

```
import asyncio
import time


def line_task(input_info):
    while True:
        time.sleep(1)
        print(input_info)


async def asyncio_task(input_info):
    while True:
        await asyncio.sleep(1)
        print(input_info)


input_info = "test"

if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation, shutdown
    from task_scheduling.scheduler import io_liner_task

    task_id1 = task_creation(None,
                             # This is how long the delay is executed (in seconds)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the daily_time is not required
                             None,
                             # This is to be performed at what point (24-hour clock)
                             # This parameter is required when the function_type is "timer",if this parameter is used, the delay is not required
                             'io',
                             # Running function type, there are "io, cpu, timer"
                             True,
                             # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
                             "task1",
                             # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
                             line_task,
                             # The function to be executed, parameters should not be passed here
                             input_info
                             # Pass the parameters required by the function, no restrictions
                             )

    time.sleep(2.0)
    io_liner_task.force_stop_task(task_id1)

    # | Io linear task | 79a85db4-c75f-4acd-a2b1-d375617e5af4 | was cancelled

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        shutdown(True)

```

### shutdown(force_cleanup: bool) -> None:

Once the task has been submitted, it is necessary to call this function to clean it up when exiting. Forced cleanup will
interrupt all running tasks, but not if set to False

```
  from task_scheduling.task_creation import shutdown
```

### update_config(key: str, value: Any) -> bool:

Update the parameters in the configuration file, note that this change will not work after a restart

```
from task_scheduling import update_config
```

# Profiles

Files are stored in:`task_scheduling/config/config.yaml`

The maximum number of CPU-optimized asynchronous tasks of the same type can run

`cpu_asyncio_task: 4`

The maximum number of tasks of the same type in an IO intensive asynchronous task

`io_asyncio_task: 4`

The maximum number of CPU-oriented linear tasks of the same type can run

`cpu_liner_task: 4`

The maximum number of tasks of the same type in an I-O intensive linear task

`io_liner_task: 4`

The timer performs the most tasks

`timer_task: 30`

When there are no tasks for many seconds, close the task scheduler(seconds)

`max_idle_time: 60`

When a task runs for a long time without finishing, it is forced to end(seconds)

`watch_dog_time: 80`

The maximum number of records that can be stored in a task status

`maximum_task_info_storage: 20`

How many seconds to check whether the task status is correct,recommended a longer interval(seconds)

`status_check_interval: 800`

Whether to enable thread management in the process

`thread_management: False`

### If you have a better idea, feel free to submit a PR

# Reference libraries:

In order to facilitate subsequent modifications,

some files are placed directly into the folder instead of being installed via pip,

so the libraries used are specifically stated here:https://github.com/glenfant/stopit