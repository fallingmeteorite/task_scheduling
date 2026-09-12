import threading
import time
from task_scheduling.construct import wait_branch_thread_ended, branch_thread_control


@wait_branch_thread_ended
def main_task(share_info, sharedtaskdict, task_signal_transmission, input_info):
    task_name = "other_task"
    timeout_processing = True

    @branch_thread_control(share_info, sharedtaskdict, timeout_processing, task_name)
    def other_task(input_info):
        while True:
            time.sleep(1)
            print(input_info)

    threading.Thread(target=other_task, args=(input_info,), daemon=True).start()

    # Use this statement to terminate the branch thread
    # time.sleep(4)
    # task_signal_transmission[sharedtaskdict.read(task_name)] = ["kill"]


if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation
    from task_scheduling.manager import task_scheduler
    from task_scheduling.server_webui import start_task_status_ui
    from task_scheduling.variable import *

    start_task_status_ui()

    task_id1 = task_creation(
        None, None, FUNCTION_TYPE_CPU, True, "linear_task",
        main_task, priority_low, "test")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler()