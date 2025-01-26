## introduce:

This python library is mainly used for task scheduling,
for example, there are a bunch of tasks here, the same type of tasks must be queued for execution,
and the tasks need strong management and monitoring

Asynchronous code and normal code are now supported,
specifically with event loops for asynchronous code

## Feature description

1.You can send a termination command to the execution code

2.You can enable timeout processing for a task, and terminate the task if it runs for too long

3.When a task fails to run, it can be added to the disabled list and will not be executed thereafter

4.You can directly obtain the current task status through the interface, such as executing, completed, error, and
timeout

5.Automatically hibernate when there are no tasks

!!! WARNING: If the task is running in a series of blocked tasks such as `time.sleep`, the task cannot be forcibly
terminated,
so use `await asyncio.sleep` for asynchronous tasks

## Installation

```
pip install task_scheduling
```

# Function introduction

### add_task(timeout_processing: bool, task_name: str, func: Callable, *args, **kwargs) -> None:

```

import asyncio
import time

from task_scheduling import add_task, shutdown


def line_task1(input_info):
    while True:
        time.sleep(5)
        print(input_info)


async def line_task2(input_info):
    while True:
        await asyncio.sleep(5)
        print(input_info)


input_info = "test"

task_id1 = add_task(True,
                    # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
                    "task1",
                    # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
                    line_task1,  # The function to be executed, parameters should not be passed here
                    input_info  # Pass the parameters required by the function, no restrictions
                    )

task_id2 = add_task(True,
                    # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
                    "task2",
                    # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
                    line_task2,  # The function to be executed, parameters should not be passed here
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

### ban_task_id(task_name: str) -> None:

```

import asyncio
import time

from task_scheduling import linetask, add_task, shutdown, asyntask


def line_task1(input_info):
    while True:
        time.sleep(5)
        print(input_info)

async def line_task2(input_info):
    while True:
        await asyncio.sleep(5)
        print(input_info)

input_info = "test"

add_task(True,
         "task1",
         line_task1,
         input_info
         )

linetask.ban_task_id("task1")
# Task Name task1 has been banned from execution

add_task(True,
         "task1",
         line_task1,
         input_info
         )

# Task 7fadcc68-8291-4924-af95-75e28a151c19 is banned and will be deleted

add_task(True,
         "task2",
         line_task2,
         input_info
         )

asyntask.ban_task_id("task2")
# Task Name task2 has been banned from execution

add_task(True,
         "task2",
         line_task2,
         input_info
         )
# Task 3fa166a3-a52b-4610-bf37-9fe5cd820199 is banned and will be deleted

try:
    while True:
        pass
except KeyboardInterrupt:
    shutdown(True)

# Prohibits the continuation of a certain type of task
# Both asyntask and linetask contain this function, and the usage method is the same

```

### allow_task_id(task_name: str) -> None:

```
import asyncio
import time

from task_scheduling import linetask, add_task, shutdown, asyntask


def line_task1(input_info):
    while True:
        time.sleep(5)
        print(input_info)


async def line_task2(input_info):
    while True:
        await asyncio.sleep(5)
        print(input_info)


input_info = "test"

add_task(True,
         "task1",
         line_task1,
         input_info
         )

linetask.ban_task_id("task1")
# Task Name task1 has been banned from execution

add_task(True,
         "task1",
         line_task1,
         input_info
         )

# Task 78b44b9e-67ae-4b29-84b0-90a408ea0c11 is banned and will be deleted

linetask.allow_task_id("task1")

# Task Name task1 has been allowed for execution

add_task(True,
         "task1",
         line_task1,
         input_info
         )

add_task(True,
         "task2",
         line_task2,
         input_info
         )

asyntask.ban_task_id("task2")
# Task Name task2 has been banned from execution

add_task(True,
         "task2",
         line_task2,
         input_info
         )
# Task 3fa166a3-a52b-4610-bf37-9fe5cd820199 is banned and will be deleted

asyntask.allow_task_id("task2")

# Task Name task2 has been allowed for execution

add_task(True,
         "task2",
         line_task2,
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
import time

from task_scheduling import linetask, add_task, shutdown, asyntask


def line_task1(input_info):
    while True:
        time.sleep(5)
        print(input_info)


async def line_task2(input_info):
    while True:
        await asyncio.sleep(5)
        print(input_info)


input_info = "test"

add_task(True,
         "task1",
         line_task1,
         input_info
         )
add_task(True,
         "task1",
         line_task1,
         input_info
         )

add_task(True,
         "task1",
         line_task1,
         input_info
         )

add_task(True,
         "task2",
         line_task2,
         input_info
         )
add_task(True,
         "task2",
         line_task2,
         input_info
         )
add_task(True,
         "task2",
         line_task2,
         input_info
         )

linetask.cancel_all_queued_tasks_by_name("task1")
asyntask.cancel_all_queued_tasks_by_name("task2")
# Task Name task1 is waiting to be executed in the queue, has been deleted
# Task Name task1 is waiting to be executed in the queue, has been deleted
try:
    while True:
        time.sleep(2)
except KeyboardInterrupt:
    shutdown(True)

# This code will delete all tasks with ID task1 in the queue
# Both asyntask and linetask contain this function, and the usage method is the same             
            
```

### force_stop_task(task_id: str) -> None:

```
import asyncio
import time

from task_scheduling import linetask, add_task, shutdown, asyntask


def line_task1(input_info):
    while True:
        time.sleep(5)
        print(input_info)


async def line_task2(input_info):
    while True:
        await asyncio.sleep(5)
        print(input_info)


input_info = "test"

task_id1 = add_task(True,
                    "task1",
                    line_task1,
                    input_info
                    )

task_id2 = add_task(True,
                    "task1",
                    line_task2,
                    input_info
                    )

time.sleep(2)
linetask.force_stop_task(task_id1)
asyntask.force_stop_task(task_id2)

# | Queue task | 619199e4-c6b5-4a10-ad31-90a23560eb1f | was cancelled
# | Linear queue task | 5e3261e8-ad43-430f-b33f-1b9eda4ac552 | timed out, forced termination
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

from task_scheduling import add_task, linetask, shutdown, asyntask


def line_task1(input_info):
    time.sleep(5)
    return input_info


async def line_task2(input_info):
    await asyncio.sleep(5)
    return input_info


input_info = "test"

task_id1 = add_task(True, "sleep", line_task1, input_info)

task_id2 = add_task(True, "sleep", line_task2, input_info)

while True:
    result = linetask.get_task_result(task_id1)
    if result is not None:
        print(f"Task result: {result}")
        break
    time.sleep(0.5)
# Task result: test
while True:
    result = asyntask.get_task_result(task_id2)
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

from task_scheduling import get_all_queue_info, add_task, shutdown


def line_task1(input_info):
    time.sleep(5)
    return input_info


async def line_task2(input_info):
    await asyncio.sleep(5)
    return input_info


input_info = "test"

add_task(True,
         "task1",
         line_task1,
         input_info
         )

add_task(True,
         "task1",
         line_task2,
         input_info
         )
time.sleep(1.0)
print(get_all_queue_info("line", True))
# line queue size: 0, Running tasks count: 1, Failed tasks count: 0
# Name: task1, ID: 736364d9-1e3a-4746-8c6b-be07178a876b, Process Status: running, Elapsed Time: 1.00 seconds

print(get_all_queue_info("line", False))
# line queue size: 0, Running tasks count: 1, Failed tasks count: 0
# Name: task1, Process Status: running, Elapsed Time: 1.00 seconds

print(get_all_queue_info("asyncio", True))

# asyncio queue size: 0, Running tasks count: 1, Failed tasks count: 0
# Name: task1, ID: 24964b35-c7a7-4206-9e89-df0ed8676caf, Process Status: running, Elapsed Time: 1.00 seconds

print(get_all_queue_info("asyncio", False))
# asyncio queue size: 0, Running tasks count: 1, Failed tasks count: 0
# Name: task1, Process Status: running, Elapsed Time: 1.00 seconds

try:
    while True:
        pass
except KeyboardInterrupt:
    shutdown(True)
# Both asyntask and linetask contain this function, and the usage method is the same

```

### get_task_status(self, task_id: str) -> Optional[Dict]:

```
import asyncio
import time

from task_scheduling import add_task, asyntask, linetask, shutdown


def line_task1(input_info):
    time.sleep(5)
    return input_info


async def line_task2(input_info):
    await asyncio.sleep(5)
    return input_info


input_info = "test"

task_id1 = add_task(True,
         "task1",
         line_task1,
         input_info
         )

task_id2 = add_task(True,
         "task1",
         line_task2,
         input_info
         )
time.sleep(1.0)

print(linetask.get_task_status(task_id1))
# {'task_name': 'task1', 'start_time': 1737857113.7971911, 'status': 'running'}

print(asyntask.get_task_status(task_id2))
# {'task_name': 'task1', 'start_time': 1737857113.8179326, 'status': 'running'}
try:
    while True:
        pass
except KeyboardInterrupt:
    shutdown(True)
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

# Reference libraries:

In order to facilitate subsequent modifications,

some files are placed directly into the folder instead of being installed via pip,

so the libraries used are specifically stated here:https://github.com/glenfant/stopit