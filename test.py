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
    from task_scheduling.server_webui import start_task_status_ui

    start_task_status_ui()

    task_id1 = task_creation(
        None, None, FUNCTION_TYPE_IO, True, "linear_task",
        linear_task, priority_low, "Hello Linear"
    )

    task_id2 = task_creation(
        None, None, FUNCTION_TYPE_IO, True, "async_task",
        async_task, priority_low, "Hello Async"
    )
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler()