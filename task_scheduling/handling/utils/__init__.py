# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys

# Prevent errors during multi-process initialization
try:
    from .timout_base import BaseTimeout, TimeoutException, base_timetable
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['BaseTimeout', 'TimeoutException', 'base_timetable']
