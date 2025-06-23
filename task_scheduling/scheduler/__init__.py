# -*- coding: utf-8 -*-
# Linear task section
from .cpu_asyncio_task import CpuAsyncioTask
from .cpu_liner_task import CpuLinerTask

# Asynchronous task section
from .io_asyncio_task import IoAsyncioTask
from .io_liner_task import IoLinerTask

# Task timer
from .timer_task import TimerTask

io_liner_task = IoLinerTask()
io_asyncio_task = IoAsyncioTask()

cpu_liner_task = CpuLinerTask()
cpu_asyncio_task = CpuAsyncioTask()

timer_task = TimerTask()
