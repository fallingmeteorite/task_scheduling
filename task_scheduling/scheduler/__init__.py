# -*- coding: utf-8 -*-
from .cpu_async_task import CpuAsyncTask
from .cpu_liner_task import CpuLinerTask

from .io_async_task import IoAsyncTask
from .io_liner_task import IoLinerTask

from .timer_task import TimerTask
from .tag_added import FunctionRunner

from .utils import *

io_liner_task = IoLinerTask()
io_async_task = IoAsyncTask()

cpu_liner_task = CpuLinerTask()
cpu_async_task = CpuAsyncTask()

timer_task = TimerTask()

detector = AwaitDetector()
