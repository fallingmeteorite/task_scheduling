# -*- coding: utf-8 -*-
"""
import time
import asyncio
from task_scheduling import add_task


async def task1(input_info):
    await asyncio.sleep(70)
    print(input_info)


def task2(input_info):
    time.sleep(70)
    print(input_info)


input_info = "test"

add_task(True, "sleep", task1, input_info)
add_task(True, "sleep", task1, input_info)

add_task(True, "sleep", task2, input_info)

"""

"""
import time

from task_scheduling import add_task, asyntask, linetask


async def task1(input_info):
    while True:
        print(input_info)
        time.sleep(3)


def task2(input_info):
    while True:
        print(input_info)
        time.sleep(3)


input_info = "test"

asyntask.ban_task_id("sleep")
linetask.ban_task_id("sleep")

add_task(True, "sleep", task1, input_info)

add_task(True, "sleep", task2, input_info)
"""

"""
import time

from task_scheduling import add_task, asyntask, linetask


def task1(input_info):
    time.sleep(2)
    return input_info


input_info = "test"


add_task(True, "sleep", task1, input_info)


while True:
    result = linetask.get_task_result("sleep")
    if result is not None:
        print(f"Task result: {result}")
    time.sleep(0.5)
"""
