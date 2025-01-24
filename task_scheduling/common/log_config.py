# -*- coding: utf-8 -*-
import sys
import weakref

from loguru import logger

# Default log format with colors, without milliseconds, including file, function, and line number
default_format: str = (
    "<g>{time:YYYY-MM-DD HH:mm:ss}</g> "  # 时间格式为不包含秒
    "[<lvl>{level}</lvl>] "
    "<c><u>{name}:{line}</u></c> | "
    "{message}"
)

# Default log level
LOG_LEVEL = "INFO"

# Use weak reference to store the logger
_logger_ref = weakref.ref(logger)

# Logger object
logger = _logger_ref()

logger.remove()

# Configure logger with the default format and output to console
logger.add(
    sys.stdout,
    format=default_format,
    level=LOG_LEVEL,
    colorize=True,
    backtrace=True,
    diagnose=True
)
