# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Logging configuration module.

This module provides centralized logging configuration using loguru for
consistent log formatting and level management across the application.
"""

# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import sys
import os

from loguru import logger

# Hardcoded log format for performance The log format includes the timestamp, log level,
# name of the file and line number where the log was generated, and the log message
_DEFAULT_FORMAT: str = (
    "<g>{time:YYYY-MM-DD HH:mm:ss}</g> "
    # Timestamp, formatted as year-month-day hour:minute:second, displayed in green
    "<c><u>{name}:{line}</u></c> | "
    # Name of the file and line number where the log was generated, displayed in cyan with underline
    "[<lvl>{level}</lvl>] "  # Log level, automatically colored based on the level
    "{message}"  # Log message
)

# Default log level
_LOG_LEVEL: str = "INFO"

# Flag to check if logger is already configured
_logger_configured: bool = False


def set_log_level(level: str):
    """
    Dynamically set the log level for the logger.

    Args:
        level: The log level to set (e.g., "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    """
    global _LOG_LEVEL
    _LOG_LEVEL = level.upper()
    os.environ["LOG_LEVEL"] = _LOG_LEVEL  # Update environment variable

    # Reconfigure the logger
    logger.remove()
    logger.add(
        sys.stdout,
        format=_DEFAULT_FORMAT,
        level=_LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True,
        enqueue=True
    )


def configure_logger():
    """
    Configure the logger if not already configured.
    """
    global _logger_configured

    if _logger_configured:
        return

    logger.remove()

    def sink_with_exception_handling(message):
        """
        Wrap the sink function to handle exceptions that may occur when the program terminates
        """
        try:
            sys.stdout.write(message)
            sys.stdout.flush()
        except (BrokenPipeError, ValueError, RuntimeError):
            # Ignore write errors on program termination
            pass

    logger.add(
        sink_with_exception_handling,
        format=_DEFAULT_FORMAT,
        level=_LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True,
        enqueue=True
    )

    _logger_configured = True
