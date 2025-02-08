# -*- coding: utf-8 -*-
from .common import configure_logger

# Initialize logger configuration at module load
configure_logger()

from .config import ensure_config_loaded

# Initialize the config dict
ensure_config_loaded()

from .queue_info_display import get_all_queue_info
from .scheduler import *
from .task_creation import TaskScheduler

task_scheduler = TaskScheduler()

__version__ = "2.0.0"
