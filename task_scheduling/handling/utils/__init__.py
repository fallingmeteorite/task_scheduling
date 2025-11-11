# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import sys

# Prevent errors during multi-process initialization
try:
    from .timout_base import BaseTimeout, TimeoutException, base_timeoutable
except KeyboardInterrupt:
    sys.exit(0)

__all__ = ['BaseTimeout', 'TimeoutException', 'base_timeoutable']
