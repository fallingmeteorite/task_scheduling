# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Task scheduling constants.

This module defines constants for task priorities and types,
making them easily accessible for IDE autocompletion.
"""

# Task priority constants
PRIORITY_LOW = priority_low = "low"
PRIORITY_HIGH = priority_high = "high"

# Task type constants
CPU_ASYNCIO = "cpu_asyncio_task"
IO_ASYNCIO = "io_asyncio_task"
CPU_LINER = "cpu_liner_task"
IO_LINER = "io_liner_task"
TIMER = "timer_task"

# Function type constants
FUNCTION_TYPE_IO = "io"
FUNCTION_TYPE_CPU = "cpu"
FUNCTION_TYPE_TIMER = "timer"
