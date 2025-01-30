# -*- coding: utf-8 -*-
"""
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
"""

"""
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
"""
"""
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
"""
"""
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
"""
"""
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
"""
"""
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
"""
"""
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
"""
"""
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
"""
"""
from task_scheduling import update_config
from task_scheduling.common.config import config

print(config["line_task_max"])
# 10
update_config("line_task_max", 18)
# Configuration file updated and reloaded successfully: line_task_max = 18
print(config["line_task_max"])
# 18
"""
