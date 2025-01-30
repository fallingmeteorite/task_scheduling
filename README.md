## introduce:

This python library is mainly used for task scheduling,
for example, there are a bunch of tasks here, the same type of tasks must be queued for execution,
and the tasks need strong management and monitoring

Asynchronous code and normal code are now supported,
specifically with event loops for asynchronous code

## Scope of application

This task scheduling is suitable for:

1.Network Requests: Handling multiple HTTP requests concurrently, where each request can be scheduled and executed asynchronously.

2.File I/O Operations: Reading from or writing to multiple files concurrently, especially when dealing with large files or when the I/O operations are slow.

3.Database Queries: Executing multiple database queries concurrently, especially when the queries involve waiting for database responses.

4.Web Scraping: Running multiple web scraping tasks concurrently, where each task involves fetching and processing web pages.

5.Real-time Data Processing: Processing real-time data streams, where tasks need to be executed as soon as data is available.

6.Background Tasks: Running background tasks that perform periodic operations, such as data aggregation, cleanup, or monitoring.



## Feature description

1.You can send a termination command to the execution code

2.You can enable timeout processing for a task, and terminate the task if it runs for too long

3.When a task fails to run, it can be added to the disabled list and will not be executed thereafter

4.You can directly obtain the current task status through the interface, such as executing, completed, error, and
timeout

5.Automatically hibernate when there are no tasks

!!! WARNING: If the task is running in a series of blocked tasks such as `time.sleep`, the task cannot be forcibly
terminated, It is recommended to use `interruptible_sleep` instead for long waits
so use `await asyncio.sleep` for asynchronous tasks

## Installation

```
pip install task_scheduling
```

# Function introduction

### add_task(timeout_processing: bool, task_name: str, func: Callable, *args, **kwargs) -> None:

```

import asyncio

from task_scheduling import add_task, shutdown, interruptible_sleep


def line_task(input_info):
    while True:
        interruptible_sleep(5)
        print(input_info)


async def asyncio_task(input_info):
    while True:
        await asyncio.sleep(5)
        print(input_info)


input_info = "test"

task_id1 = add_task(True,
                    # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
                    "task1",
                    # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
                    line_task,  # The function to be executed, parameters should not be passed here
                    input_info  # Pass the parameters required by the function, no restrictions
                    )

task_id2 = add_task(True,
                    # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
                    "task2",
                    # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
                    asyncio_task,  # The function to be executed, parameters should not be passed here
                    input_info  # Pass the parameters required by the function, no restrictions
                    )

print(task_id1, task_id2)
# cf478b6e-5e02-49b8-9031-4adc6ff915c2, cf478b6e-5e02-49b8-9031-4adc6ff915c2

try:
    while True:
        pass
except KeyboardInterrupt:
    shutdown(True)
```

### ban_task_name(task_name: str) -> None:

```

import asyncio

from task_scheduling import io_async_task, add_task, shutdown, io_liner_task, interruptible_sleep


def line_task(input_info):
    while True:
        interruptible_sleep(5)
        print(input_info)


async def asyncio_task(input_info):
    while True:
        await asyncio.sleep(5)
        print(input_info)


input_info = "test"

add_task(True,
         "task1",
         line_task,
         input_info
         )

io_liner_task.ban_task_name("task1")
# | Io linear task | task1 | is banned from execution

add_task(True,
         "task1",
         line_task,
         input_info
         )

# | Io linear task | eff3daf0-96f4-4d04-abd8-36bdfae16aa9 | is banned and will be deleted

add_task(True,
         "task2",
         asyncio_task,
         input_info
         )

io_async_task.ban_task_name("task2")
# | Io asyncio task | task2 | has been banned from execution

add_task(True,
         "task2",
         asyncio_task,
         input_info
         )
# Io asyncio task | bafe8026-68d7-4753-9a55-bde5608c3dcb | is banned and will be deleted

try:
    while True:
        pass
except KeyboardInterrupt:
    shutdown(True)

# Prohibits the continuation of a certain type of task
# Both asyntask and linetask contain this function, and the usage method is the same

```

### allow_task_name(task_name: str) -> None:

```
import asyncio

from task_scheduling import io_async_task, add_task, shutdown, io_liner_task, interruptible_sleep


def line_task(input_info):
    while True:
        interruptible_sleep(5)
        print(input_info)


async def asyncio_task(input_info):
    while True:
        await asyncio.sleep(5)
        print(input_info)


input_info = "test"

add_task(True,
         "task1",
         line_task,
         input_info
         )

io_liner_task.ban_task_name("task1")
# | Io linear task | task1 | is banned from execution

add_task(True,
         "task1",
         line_task,
         input_info
         )

# | Io linear task | fa0fe12f-ad7f-4016-a76a-25285e12e21e | is banned and will be deleted

io_liner_task.allow_task_name("task1")

# | Io linear task | task1 | is allowed for execution

add_task(True,
         "task1",
         line_task,
         input_info
         )

add_task(True,
         "task2",
         asyncio_task,
         input_info
         )

io_async_task.ban_task_name("task2")
# | Io asyncio task | task2 | has been banned from execution

add_task(True,
         "task2",
         asyncio_task,
         input_info
         )
# | Io asyncio task | 9747ac36-8582-4b44-80d9-1cb4d0dcd86a | is banned and will be deleted

io_async_task.allow_task_name("task2")

# | Io asyncio task | task2 | is allowed for execution

add_task(True,
         "task2",
         asyncio_task,
         input_info
         )

try:
    while True:
        pass
except KeyboardInterrupt:
    shutdown(True)
             
# Removal of the ban on such tasks
# Both asyntask and linetask contain this function, and the usage method is the same
```

### cancel_all_queued_tasks_by_name(task_name: str) -> None:

```
import asyncio

from task_scheduling import io_liner_task, add_task, shutdown, io_async_task, interruptible_sleep


def line_task(input_info):
    while True:
        interruptible_sleep(5)
        print(input_info)


async def asyncio_task(input_info):
    while True:
        await asyncio.sleep(5)
        print(input_info)


input_info = "test"

add_task(True,
         "task1",
         line_task,
         input_info
         )
add_task(True,
         "task1",
         line_task,
         input_info
         )

add_task(True,
         "task1",
         line_task,
         input_info
         )

add_task(True,
         "task2",
         asyncio_task,
         input_info
         )
add_task(True,
         "task2",
         asyncio_task,
         input_info
         )
add_task(True,
         "task2",
         asyncio_task,
         input_info
         )

io_liner_task.cancel_all_queued_tasks_by_name("task1")
io_async_task.cancel_all_queued_tasks_by_name("task2")
# | Io linear task | task1 | is waiting to be executed in the queue, has been deleted

try:
    while True:
        pass
except KeyboardInterrupt:
    shutdown(True)

# This code will delete all tasks with ID task1 in the queue
# Both asyntask and linetask contain this function, and the usage method is the same             
            
```

### force_stop_task(task_id: str) -> None:

```

import asyncio
import time

from task_scheduling import io_async_task, add_task, shutdown, io_liner_task, interruptible_sleep


def line_task(input_info):
    while True:
        interruptible_sleep(5)
        print(input_info)


async def asyncio_task(input_info):
    while True:
        await asyncio.sleep(5)
        print(input_info)


input_info = "test"

task_id1 = add_task(True,
                    "task1",
                    line_task,
                    input_info
                    )

task_id2 = add_task(True,
                    "task1",
                    asyncio_task,
                    input_info
                    )

time.sleep(3.0)
io_liner_task.force_stop_task(task_id1)
io_async_task.force_stop_task(task_id2)

# | Io linear task | fb30d17e-0b15-4a88-b8c6-cbbc8163b909 | has been forcibly cancelled
# | Io asyncio task | daa36e09-2959-44ec-98b6-8f1948535687 | has been forcibly cancelled
try:
    while True:
        pass
except KeyboardInterrupt:
    shutdown(True)
    
# This code will forcibly terminate the running task, note! Using this function during file reading or writing may cause file corruption
# Both asyntask and linetask contain this function, and the usage method is the same     
   
```

### get_task_result(task_id: str) -> Optional[Any]:

```
import asyncio
import time

from task_scheduling import add_task, io_async_task, shutdown, io_liner_task, interruptible_sleep


def line_task(input_info):
    interruptible_sleep(5)
    return input_info


async def asyncio_task(input_info):
    await asyncio.sleep(5)
    return input_info


input_info = "test"

task_id1 = add_task(True,
                    "sleep",
                    line_task,
                    input_info)

task_id2 = add_task(True,
                    "sleep",
                    asyncio_task,
                    input_info)

while True:
    result = io_liner_task.get_task_result(task_id1)
    if result is not None:
        print(f"Task result: {result}")
        break
    time.sleep(0.5)
# Task result: test
while True:
    result = io_async_task.get_task_result(task_id2)
    if result is not None:
        print(f"Task result: {result}")
        break
    time.sleep(0.5)

# Task result: test
try:
    while True:
        pass
except KeyboardInterrupt:
    shutdown(True)
    
# Both asyntask and linetask contain this function, and the usage method is the same

```

### get_all_queue_info(queue_type: str, show_id: bool) -> str:

```
import asyncio
import time

from task_scheduling import get_all_queue_info, add_task, shutdown, interruptible_sleep


def line_task(input_info):
    interruptible_sleep(5)
    return input_info


async def asyncio_task(input_info):
    await asyncio.sleep(5)
    return input_info


input_info = "test"

add_task(True,
         "task1",
         line_task,
         input_info
         )

add_task(True,
         "task1",
         asyncio_task,
         input_info
         )

time.sleep(1.0)
# line queue size: 0, Running tasks count: 1
# Name: task1, ID: 736364d9-1e3a-4746-8c6b-be07178a876b, Process Status: running, Elapsed Time: 1.00 seconds


# asyncio queue size: 0, Running tasks count: 1
# Name: task1, ID: 24964b35-c7a7-4206-9e89-df0ed8676caf, Process Status: running, Elapsed Time: 1.00 seconds
try:
    while True:
        print(get_all_queue_info("line", True))
        print(get_all_queue_info("asyncio", True))
        time.sleep(1.0)
except KeyboardInterrupt:
    shutdown(True)
# Both asyntask and linetask contain this function, and the usage method is the same

```

### get_task_status(self, task_id: str) -> Optional[Dict]:

```
import asyncio
import time

from task_scheduling import add_task, io_async_task, io_liner_task, shutdown, interruptible_sleep


def line_task(input_info):
    interruptible_sleep(5)
    return input_info


async def asyncio_task(input_info):
    await asyncio.sleep(5)
    return input_info


input_info = "test"

task_id1 = add_task(True,
                    "task1",
                    line_task,
                    input_info
                    )

task_id2 = add_task(True,
                    "task1",
                    asyncio_task,
                    input_info
                    )
time.sleep(1.0)

print(io_liner_task.get_task_status(task_id1))
# {'task_name': 'task1', 'start_time': 1737857113.8179326, 'status': 'running'}
print(io_async_task.get_task_status(task_id2))
# {'task_name': 'task1', 'start_time': 1737857113.8179326, 'status': 'running'}

try:
    while True:
        pass
except KeyboardInterrupt:
    shutdown(True)
    
# Returns a task status dictionary
```

### shutdown(force_cleanup: bool) -> None:

```
from task_scheduling import shutdown

# When you want to close the software, call this function to close the task scheduling

# Safely shut down and wait for the running task to end
shutdown(False)

#Forced shutdown may result in errors and file corruption
shutdown(True)
```

### interruptible_sleep(seconds: float or int) -> None:
```
from task_scheduling import interruptible_sleep

interruptible_sleep(5)
# Sleep for 5 seconds
```

# Profile settings

### update_config(key: str, value: Any) -> bool:

```
from task_scheduling import update_config

print(config["line_task_max"])
# 10

update_config("line_task_max", 18)

# Configuration file updated and reloaded successfully: line_task_max = 18

print(config["line_task_max"])

# 18


# The updated configuration is not written to the file, and the modified data is stored in memory
```

The configuration file is stored at:

`task_scheduling/common/config.yaml`

The maximum number of linear tasks that can run at the same time

`line_task_max: 10`

The maximum number of queues for a asyncio task

`maximum_queue_async: 30`

The maximum number of queues for a linear task

`maximum_queue_line: 30`

When there are no tasks for many seconds, close the task scheduler(seconds)

`max_idle_time: 60`

When a task runs for a long time without finishing, it is forced to end(seconds)

`watch_dog_time: 200`

The maximum number of records that can be stored in a task status

`maximum_task_info_storage: 60`

The maximum number of tasks that run in a single event loop

`maximum_event_loop_tasks: 3`

How many seconds to check whether the task status is correct,recommended a longer interval(seconds)

`status_check_interval: 800`

# Reference libraries:

In order to facilitate subsequent modifications,

some files are placed directly into the folder instead of being installed via pip,

so the libraries used are specifically stated here:https://github.com/glenfant/stopit