# -*- coding: utf-8 -*-
from .common import configure_logger

# Initialize logger configuration at module load
configure_logger()

from .config import ensure_config_loaded

# Initialize the config dict
ensure_config_loaded()

from .queue_info_display import get_tasks_info
from .scheduler import *
from .task_creation import task_creation
from .scheduler_management import shutdown

__version__ = "2.0.0"
