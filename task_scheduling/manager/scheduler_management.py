from ..common.log_config import logger
from ..scheduler import io_async_task, io_liner_task, cpu_liner_task, timer_task






def shutdown(force_cleanup: bool) -> None:
    """
    :param force_cleanup: Force the end of a running task

    Shutdown the scheduler, stop all tasks, and release resources.
    Only checks if the scheduler is running and forces a shutdown if necessary.
    """
    # Shutdown asynchronous task scheduler if running
    if hasattr(timer_task, "scheduler_started") and timer_task.scheduler_started:
        logger.info("Detected Cpu linear task scheduler is running, shutting down...")
        timer_task.stop_all_schedulers(force_cleanup)
        logger.info("Cpu linear task scheduler has been shut down.")

    # Shutdown asynchronous task scheduler if running
    if hasattr(cpu_liner_task, "scheduler_started") and cpu_liner_task.scheduler_started:
        logger.info("Detected Cpu linear task scheduler is running, shutting down...")
        cpu_liner_task.stop_all_schedulers(force_cleanup)
        logger.info("Cpu linear task scheduler has been shut down.")

    # Shutdown asynchronous task scheduler if running
    if hasattr(io_async_task, "scheduler_started") and io_async_task.scheduler_started:
        logger.info("Detected io asyncio task scheduler is running, shutting down...")
        io_async_task.stop_all_schedulers(force_cleanup)
        logger.info("Io asyncio task scheduler has been shut down.")

    # Shutdown linear task scheduler if running
    if hasattr(io_liner_task, "scheduler_started") and io_liner_task.scheduler_started:
        logger.info("Detected io linear task scheduler is running, shutting down...")
        io_liner_task.stop_scheduler(force_cleanup)
        logger.info("Io linear task scheduler has been shut down.")

    logger.info("All scheduler has been shut down.")
