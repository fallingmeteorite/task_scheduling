# from task_scheduling.utils import FunctionRunner
"""
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
"""

# from task_scheduling.function_data import task_function_type
"""
if __name__ == "__main__":
    from task_scheduling.function_data import task_function_type

    task_function_type.append_to_dict("CPU_Task", "test")

    print(task_function_type.read_from_dict("CPU_Task"))
    print(task_function_type.read_from_dict("CPU_Task"))

"""

# from task_scheduling.task_creation import task_creation, shutdown
# (The task is of the "io" type)
"""
import asyncio

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
            pass
    except KeyboardInterrupt:
        shutdown(True)
"""
# from task_scheduling.task_creation import task_creation, shutdown
# (The task is of the "timer" type)
"""
from task_scheduling.utils import interruptible_sleep


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
            pass
    except KeyboardInterrupt:
        shutdown(True)

"""

# from task_scheduling.task_creation import task_creation, shutdown
# (The task is of the "cpu" type)
"""
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
                             asyncio_task,
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
                             'cpu',
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
    time.sleep(1.0)
    shutdown(True)
    try:
        while True:
            time.sleep(0.5)
            pass
    except KeyboardInterrupt:
        pass

"""

# from task_scheduling.scheduler import io_liner_task
# io_liner_task.get_task_result(task_id1)
"""
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

"""
# from task_scheduling.queue_info_display import get_tasks_info
"""
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

"""
# from task_scheduling.task_creation import task_scheduler

"""
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

"""
# from task_scheduling.task_creation import task_scheduler
"""
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

    task_scheduler.cancel_the_queue_task_by_name("task1")

    # This type of name task has been removed

    try:
        while True:
            time.sleep(2.0)
    except KeyboardInterrupt:
        shutdown(True)

"""
# from task_scheduling.scheduler import io_async_task
"""
import asyncio
import time


def line_task(input_info):
    while True:
        interruptible_sleep(2)
        print(input_info)


async def asyncio_task(input_info):
    while True:
        await asyncio.sleep(2)
        print(input_info)


input_info = "test"
if __name__ == "__main__":
    from task_scheduling.scheduler import io_async_task
    from task_scheduling.utils import interruptible_sleep
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
                             asyncio_task,
                             # The function to be executed, parameters should not be passed here
                             input_info
                             # Pass the parameters required by the function, no restrictions
                             )

    time.sleep(3.0)
    io_async_task.force_stop_task(task_id1)

    # | Io asyncio task | 2d77dd07-73a6-42e8-9032-6b051ce310f2 | was cancelled

    try:
        while True:
            time.sleep(2.0)
    except KeyboardInterrupt:
        shutdown(True)

"""
