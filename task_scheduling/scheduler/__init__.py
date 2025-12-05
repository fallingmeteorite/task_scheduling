# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Initialize available methods
"""
import sys
import sysconfig

# Prevent errors during multi-process initialization
try:
    from task_scheduling.scheduler.api import add_api, kill_api, pause_api, resume_api, get_result_api, shutdown_api, \
        cleanup_results_api

    if sysconfig.get_config_var("Py_GIL_DISABLED") == 1:
        from task_scheduling.common import logger, config

        logger.warning("Currently running in no GIL mode!")
        logger.error(
            f"The memory usage for submissions in this mode is too high. Please make sure your computer has more than(When fully loaded): {config["io_liner_task"] / 2 * 0.1}GB!")
        logger.error("This number comes from the maximum number of tasks that your thread pool can run(When fully loaded)!")
        logger.error(
            "This number is the minimum threshold. If the code uses too much memory, this value should be increased(When fully loaded)!")

except KeyboardInterrupt:
    sys.exit(0)
__all__ = ['add_api', 'kill_api', 'pause_api', 'resume_api', 'get_result_api', 'shutdown_api',
           'cleanup_results_api']
