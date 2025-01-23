"""
Examples::
>>> from scheduling import add_task
>>> import time
>>> print_info = "test"
>>> async def test_async(print_info):
>>>     time.sleep(10)
>>>     return print_info
>>>
>>> def test_line(print_info):
>>>     time.sleep(10)
>>>     return print_info
>>>
>>> add_task(True, "sleep", test_async, print_info)
>>>
>>> add_task(False, "sleep", test_async, print_info)
>>>
>>> add_task(True, "sleep", test_line, print_info)

Examples::
>>> from scheduling import get_all_queue_info
>>>
>>> get_all_queue_info("asyncio")
>>> get_all_queue_info("line")

Examples::
>>> # Continuously get task results
>>> from scheduling import linetask
>>> import time
>>> while True:
>>>     result = linetask.get_task_result("task_id")
>>>     if result is not None:
>>>         print(f"Task result: {result}")
>>>     time.sleep(0.5)  # Check every 0.5 seconds
>>>
>>> # Continuously get task results
>>> from scheduling import asyntask
>>> while True:
>>>     result = asyntask.get_task_result("task_id")
>>>     if result is not None:
>>>         print(f"Task result: {result}")
>>>     time.sleep(0.5)  # Check every 0.5 seconds

Examples::
>>> from scheduling import asyntask, linetask
>>> linetask.ban_task_id("task_id")
>>> asyntask.ban_task_id("task_id")
>>> # Force stop a specified running task
>>> linetask.force_stop_task("task_id")
>>> asyntask.force_stop_task("task_id")
>>> # Cancel all queued tasks with the specified name
>>> linetask.cancel_all_queued_tasks_by_name("task_name")
>>> asyntask.cancel_all_queued_tasks_by_name("task_name")
"""
