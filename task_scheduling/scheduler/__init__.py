# -*- coding: utf-8 -*-
# Author: fallingmeteorite
# Linear task section
from .cpu_asyncio_task import cpu_asyncio_task
from .cpu_liner_task import cpu_liner_task

# Asynchronous task section
from .io_asyncio_task import io_asyncio_task
from .io_liner_task import io_liner_task

# Task timer
from .timer_task import timer_task

from .share import shared_task_info

import sysconfig
if sysconfig.get_config_var("Py_GIL_DISABLED") == 1:
    from ..common import logger
    logger.warning("Free threaded is enabled")





