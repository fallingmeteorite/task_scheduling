# (The task is of the "io" type)
"""
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
"""
# (The task is of the "timer" type)
"""
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
"""
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
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        shutdown(True)

"""

# A task that detects what type of function is executed
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

# Add a function type and a view type

"""
if __name__ == "__main__":
    from task_scheduling.function_data import task_function_type

    task_function_type.append_to_dict("CPU_Task", "test")

    print(task_function_type.read_from_dict("CPU_Task"))
    print(task_function_type.read_from_dict("CPU_Task"))
"""
# Get the data returned by the task
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
# Get information on all tasks
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
"""

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
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        shutdown(True)

"""
# Get information about a single task
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
"""

# Add and remove disabled task names
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
# Cancel a task that is being queued
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
"""
# All 4 schedulers have this function for terminating a running task
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

"""

"""
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
    time.sleep(2.0)
    shutdown(True)
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass

"""
