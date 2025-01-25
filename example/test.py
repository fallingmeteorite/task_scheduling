# -*- coding: utf-8 -*-
"""
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
"""

"""
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
"""

"""
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
"""

"""
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

"""

"""
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
"""

"""
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
"""
"""
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
print(get_all_queue_info("line"))
# line queue size: 0, Running tasks count: 1
# Name: task1, ID: 736364d9-1e3a-4746-8c6b-be07178a876b, Process Status: running, Elapsed Time: 1.00 seconds

print(get_all_queue_info("asyncio"))

# asyncio queue size: 0, Running tasks count: 1
# Name: task1, ID: 24964b35-c7a7-4206-9e89-df0ed8676caf, Process Status: running, Elapsed Time: 1.00 seconds
try:
    while True:
        pass
except KeyboardInterrupt:
    shutdown(True)
"""
"""
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

print(asyntask.get_task_status(task_id2))

try:
    while True:
        pass
except KeyboardInterrupt:
    shutdown(True)
"""
"""
from task_scheduling import update_config

update_config("line_task_max", 10)
"""