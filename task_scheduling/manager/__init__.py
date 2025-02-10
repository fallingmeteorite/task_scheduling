# -*- coding: utf-8 -*-
from .task_details_queue import TaskStatusManager

# Shared by all schedulers, instantiating objects
task_status_manager = TaskStatusManager()
