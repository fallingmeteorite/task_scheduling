import io
import sys
import types
import unittest
from unittest.mock import Mock, patch


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
        UnpicklingError=ValueError,
    )

if "loguru" not in sys.modules:
    sys.modules["loguru"] = types.SimpleNamespace(logger=_FakeLogger())

from task_scheduling.common import ensure_config_loaded

ensure_config_loaded()

import task_scheduling.server_webui.ui as webui_module


class _SnapshotOnlyStatusManager:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    @property
    def _task_status_dict(self):
        raise AssertionError("private task status dict should not be accessed directly")

    def get_all_task_statuses(self):
        return self.snapshot


class _BrokenPipeWriter(io.BytesIO):
    def write(self, data):
        raise BrokenPipeError("client disconnected")


class StatusApiReviewBatchTests(unittest.TestCase):
    def test_get_tasks_info_uses_status_manager_snapshot(self):
        snapshot = {
            "task-1": {
                "task_name": "demo",
                "status": "running",
                "task_type": "io_liner_task",
                "start_time": None,
                "priority": "low",
            }
        }

        with patch.object(webui_module, "task_status_manager", _SnapshotOnlyStatusManager(snapshot)):
            result = webui_module.get_tasks_info()

        self.assertEqual(result["running_count"], 1)
        self.assertEqual(result["tasks"][0]["id"], "task-1")

    def test_handle_tasks_ignores_broken_pipe(self):
        handler = webui_module.TaskControlHandler.__new__(webui_module.TaskControlHandler)
        handler.wfile = _BrokenPipeWriter()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()

        with patch.object(webui_module, "get_tasks_info", return_value={"tasks": []}):
            webui_module.TaskControlHandler._handle_tasks(handler)

        handler.send_response.assert_called_once_with(200)

    def test_handle_task_addition_status_ignores_broken_pipe(self):
        handler = webui_module.TaskControlHandler.__new__(webui_module.TaskControlHandler)
        handler.wfile = _BrokenPipeWriter()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()

        with patch.object(webui_module, "get_task_addition_status", return_value={"enabled": True}):
            webui_module.TaskControlHandler._handle_task_addition_status(handler)

        handler.send_response.assert_called_once_with(200)


if __name__ == "__main__":
    unittest.main()
