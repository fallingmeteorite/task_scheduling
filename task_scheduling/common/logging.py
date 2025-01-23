# -*- coding: utf-8 -*-
import atexit
import weakref
from loguru import logger as loguru_logger

# Default log format with colors
default_format: str = (
    "<g>{time:MM-DD HH:mm:ss}</g> "
    "[<lvl>{level}</lvl>] "
    "<c><u>{name}</u></c> | "
    "{message}"
)

# Alternative plain log format without colors
plain_format: str = (
    "{time:MM-DD HH:mm:ss} "
    "[{level}] "
    "{name} | "
    "{message}"
)

# Default log level
LOG_LEVEL = "INFO"

# Use weak reference to store the logger
_logger_ref = weakref.ref(loguru_logger)

# Logger object
logger = _logger_ref()

# Register a function to close the logger when the program exits
atexit.register(lambda: _logger_ref().remove())
