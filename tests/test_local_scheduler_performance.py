import importlib
import sys
import threading
import types
import unittest
from unittest import mock

import loguru


def _load_module(module_name):
    sys.modules["dill"] = types.SimpleNamespace(
        dumps=lambda value: value,
        loads=lambda value: value,
    )
    loguru.logger.add = lambda *args, **kwargs: 1
    loguru.logger.remove = lambda *args, **kwargs: None
    return importlib.import_module(module_name)


class TaskSchedulerGcTests(unittest.TestCase):
    def test_gc_runs_once_per_threshold_window(self):
        scheduler_manager = _load_module("task_scheduling.manager.scheduler_manager")
        scheduler = scheduler_manager.TaskScheduler()
        scheduler.allocator_started = True

        with mock.patch.object(
            type(scheduler_manager.task_status_manager),
            "add_task_status",
            return_value=None,
        ), mock.patch.object(scheduler_manager.gc, "collect", return_value=0) as collect_mock:
            for index in range(41):
                added = scheduler.add_task(
                    None,
                    None,
                    False,
                    "io",
                    False,
                    f"task-{index}",
                    f"id-{index}",
                    lambda: None,
                    "low",
                )
                self.assertTrue(added)

        self.assertEqual(collect_mock.call_count, 1)
        self.assertEqual(scheduler._task_counter, 1)


class CleanupResultsTests(unittest.TestCase):
    def test_cleanup_prunes_expired_results_in_place(self):
        scheduler_api = _load_module("task_scheduling.scheduler.api")

        class DummyHandler:
            def __init__(self):
                self._lock = threading.Lock()
                self._task_results = {
                    "expired": ["old", 10],
                    "fresh": ["new", 90],
                }

        handler = DummyHandler()
        original_mapping = handler._task_results

        scheduler_api._cleanup_task_results(
            handler,
            current_time=100,
            max_result_count=1,
            max_result_age=20,
        )

        self.assertIs(handler._task_results, original_mapping)
        self.assertEqual(handler._task_results, {"fresh": ["new", 90]})


class RunningTaskNameIndexTests(unittest.TestCase):
    def test_io_liner_rejects_duplicate_name_from_running_name_index(self):
        io_liner_module = _load_module("task_scheduling.scheduler.io_liner_task")
        scheduler = io_liner_module.IoLinerTask()
        scheduler._scheduler_started = True
        scheduler._running_task_names.add("duplicate-name")

        with mock.patch.object(
            type(io_liner_module.task_status_manager),
            "add_task_status",
            return_value=None,
        ):
            added = scheduler.add_task(
                False,
                "duplicate-name",
                "task-id",
                lambda: None,
                "low",
            )

        self.assertFalse(added)


if __name__ == "__main__":
    unittest.main()
