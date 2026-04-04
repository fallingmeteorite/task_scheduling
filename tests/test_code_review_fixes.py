import queue
import sys
import types
import unittest
from concurrent.futures import Future
from unittest.mock import patch


class _FakeLogger:
    def add(self, *args, **kwargs):
        return 1

    def remove(self, *args, **kwargs):
        return None

    def debug(self, *args, **kwargs):
        return None

    info = debug
    warning = debug
    error = debug
    critical = debug


if "dill" not in sys.modules:
    sys.modules["dill"] = types.SimpleNamespace(
        dumps=lambda obj, *args, **kwargs: obj,
        loads=lambda obj, *args, **kwargs: obj,
    )

if "loguru" not in sys.modules:
    sys.modules["loguru"] = types.SimpleNamespace(logger=_FakeLogger())

from task_scheduling.common import ensure_config_loaded
from task_scheduling.scheduler.utils.priority_check import TaskCounter

ensure_config_loaded()

import task_scheduling.scheduler.cpu_liner_task as cpu_liner_module
import task_scheduling.scheduler.io_liner_task as io_liner_module
import task_scheduling.scheduler.timer_task as timer_module


def _dummy_task():
    return "ok"


class CodeReviewFixTests(unittest.TestCase):
    def test_io_linear_high_priority_task_can_preempt_when_full(self):
        scheduler = io_liner_module.IoLinerTask()
        scheduler._running_tasks["low-1"] = [Future(), "low-task", "low"]
        task_counter = TaskCounter("io_liner_task")

        with patch.dict(io_liner_module.config, {"io_liner_task": 1}, clear=False), \
                patch.object(io_liner_module, "_task_counter", task_counter), \
                patch("task_scheduling.scheduler.api.pause_api", return_value=True) as pause_api, \
                patch.object(type(io_liner_module.task_status_manager), "add_task_status"), \
                patch.object(io_liner_module.IoLinerTask, "_start_scheduler"), \
                patch.object(io_liner_module.IoLinerTask, "_cancel_idle_timer"):
            state = scheduler.add_task(False, "high-task", "high-1", _dummy_task, "high")

        self.assertTrue(state)
        self.assertEqual(task_counter.get_high_priority_count(), 1)
        self.assertEqual(task_counter.get_paused_queue(), ["low-1"])
        self.assertEqual(scheduler._task_queue.qsize(), 1)
        pause_api.assert_called_once_with("io_liner_task", "low-1")

    def test_cpu_linear_high_priority_task_can_preempt_when_full(self):
        scheduler = cpu_liner_module.CpuLinerTask()
        scheduler._running_tasks["low-1"] = [Future(), "low-task", "low"]
        task_counter = TaskCounter("cpu_liner_task")
        shared_status = types.SimpleNamespace(task_status_queue=queue.Queue())

        with patch.dict(cpu_liner_module.config, {"cpu_liner_task": 1}, clear=False), \
                patch.object(cpu_liner_module, "_task_counter", task_counter), \
                patch.object(cpu_liner_module, "shared_status_info_liner", shared_status), \
                patch("task_scheduling.scheduler.api.pause_api", return_value=True) as pause_api, \
                patch.object(cpu_liner_module.CpuLinerTask, "_start_scheduler"), \
                patch.object(cpu_liner_module.CpuLinerTask, "_cancel_idle_timer"):
            state = scheduler.add_task(False, "high-task", "high-1", _dummy_task, "high")

        self.assertTrue(state)
        self.assertEqual(task_counter.get_high_priority_count(), 1)
        self.assertEqual(task_counter.get_paused_queue(), ["low-1"])
        self.assertEqual(scheduler._task_queue.qsize(), 1)
        pause_api.assert_called_once_with("cpu_liner_task", "low-1")

    def test_timer_resume_uses_timer_task_type(self):
        scheduler = timer_module.TimerTask()
        scheduler._running_tasks["timer-1"] = [object(), "timer-task"]

        with patch.object(type(timer_module._task_manager), "resume_task"), \
                patch.object(type(timer_module.task_status_manager), "add_task_status") as add_status:
            state = scheduler.resume_task("timer-1")

        self.assertTrue(state)
        self.assertEqual(add_status.call_count, 1)
        self.assertEqual(add_status.call_args.args[-1], "timer_task")

    def test_io_linear_done_marks_unhandled_errors_as_failed(self):
        scheduler = io_liner_module.IoLinerTask()
        future = Future()
        future.set_exception(RuntimeError("boom"))
        scheduler._running_tasks["task-1"] = [future, "task-name", "low"]

        fake_counter = types.SimpleNamespace(remove_high_priority_task=lambda task_id: None)

        with patch.object(io_liner_module, "_task_counter", fake_counter), \
                patch.object(type(io_liner_module.task_status_manager), "add_task_status") as add_status, \
                patch.object(io_liner_module.IoLinerTask, "_reset_idle_timer"), \
                patch.dict(io_liner_module.config, {"network_storage_results": False}, clear=False):
            scheduler._task_done("task-1", future)

        self.assertEqual(add_status.call_count, 1)
        self.assertEqual(add_status.call_args.args[2], "failed")
        self.assertEqual(scheduler._task_results["task-1"][0], "failed action")

    def test_timer_done_marks_unhandled_errors_as_failed(self):
        scheduler = timer_module.TimerTask()
        future = Future()
        future.set_exception(RuntimeError("boom"))
        scheduler._running_tasks["task-1"] = [future, "task-name"]

        with patch.object(type(timer_module.task_status_manager), "add_task_status") as add_status, \
                patch.object(timer_module.TimerTask, "_reset_idle_timer"), \
                patch.dict(timer_module.config, {"network_storage_results": False}, clear=False):
            scheduler._task_done("task-1", False, "task-name", _dummy_task, (), {}, future)

        self.assertEqual(add_status.call_count, 1)
        self.assertEqual(add_status.call_args.args[2], "failed")
        self.assertEqual(scheduler._task_results["task-1"][0], "failed action")


if __name__ == "__main__":
    unittest.main()
