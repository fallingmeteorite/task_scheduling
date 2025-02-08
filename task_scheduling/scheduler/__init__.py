# -*- coding: utf-8 -*-
# Linear task section
from .cpu_asyncio_task import CpuAsyncTask
from .cpu_liner_task import CpuLinerTask

# Asynchronous task section
from .io_asyncio_task import IoAsyncTask
from .io_liner_task import IoLinerTask

# Used for task tagging
from .tag_added import FunctionRunner

# Task timer
from .timer_task import TimerTask

from .utils import *

io_liner_task = IoLinerTask()
io_async_task = IoAsyncTask()

cpu_liner_task = CpuLinerTask()
cpu_async_task = CpuAsyncTask()

timer_task = TimerTask()

detector = AwaitDetector()
