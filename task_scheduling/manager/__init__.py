# -*- coding: utf-8 -*-
# Author: fallingmeteorite
from .task_details_manager import TaskStatusManager

# Shared by all schedulers, instantiating objects
task_status_manager = TaskStatusManager()

from .thread_info_share import SharedTaskDict


from .task_info_display import get_tasks_info
