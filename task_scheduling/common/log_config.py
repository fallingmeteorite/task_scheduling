# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import sys

from loguru import logger

# Hardcoded log format for performance
# The log format includes the timestamp, log level, name of the file and line number where the log was generated, and the log message
_DEFAULT_FORMAT: str = (
    "<g>{time:YYYY-MM-DD HH:mm:ss}</g> "  # Timestamp, formatted as year-month-day hour:minute:second, displayed in green
    "[<lvl>{level}</lvl>] "  # Log level, automatically colored based on the level
    "<c><u>{name}:{line}</u></c> | "  # Name of the file and line number where the log was generated, displayed in cyan with underline
    "{message}"  # Log message
)

# Default log level
_LOG_LEVEL: str = "INFO"

# Flag to check if logger is already configured
_logger_configured: bool = False


def configure_logger():
    """
    Configure the logger if not already configured.
    """
    global _logger_configured

    # Skip configuration if the logger is already set up
    if _logger_configured:
        return

    # Remove all default handlers if necessary
    logger.remove()

    # Configure logger to output to console with the specified format, level, and features
    logger.add(
        sys.stdout,
        format=_DEFAULT_FORMAT,  # Use the predefined log format
        level=_LOG_LEVEL,  # Set the default log level
        colorize=True,  # Enable log colorization
        backtrace=True,  # Enable backtrace in case of exceptions
        diagnose=True  # Enable diagnostic information in case of exceptions
    )

    # Mark the logger as configured
    _logger_configured = True

# Example log message (only for debugging)
# logger.info("Logger configuration completed")
