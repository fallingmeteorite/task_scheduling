import sys
import types
import unittest
from unittest.mock import patch


class _FakeLogger:
    def __init__(self):
        self.info_calls = []
        self.error_calls = []

    def add(self, *args, **kwargs):
        return 1

    def remove(self, *args, **kwargs):
        return None

    def debug(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def critical(self, *args, **kwargs):
        return None

    def info(self, *args, **kwargs):
        self.info_calls.append((args, kwargs))

    def error(self, *args, **kwargs):
        self.error_calls.append((args, kwargs))


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

import task_scheduling.client.rpc_client as rpc_client_module
import task_scheduling.main_server.utils.core as core_module
import task_scheduling.task_creation as task_creation_module


def _dummy_task():
    return "ok"


class _FakeScheduler:
    def __init__(self):
        self.calls = []

    def add_task(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return True


class ClientNetworkReviewFollowupTests(unittest.TestCase):
    def test_task_creation_rejects_unsupported_function_type(self):
        fake_scheduler = _FakeScheduler()

        with patch.object(task_creation_module, "task_scheduler", fake_scheduler), \
                patch.object(task_creation_module.logger, "error") as error_log:
            state = task_creation_module.task_creation(
                None, None, "normal", False, "demo-task", _dummy_task, "low"
            )

        self.assertFalse(state)
        self.assertEqual(fake_scheduler.calls, [])
        self.assertEqual(error_log.call_count, 1)

    def test_network_task_submit_rejects_unsupported_function_type(self):
        fake_scheduler = _FakeScheduler()

        with patch.object(core_module, "task_scheduler", fake_scheduler), \
                patch.object(core_module.logger, "error") as error_log:
            state = core_module.task_submit(
                "task-1", None, None, "normal", False, "demo-task", _dummy_task, "low"
            )

        self.assertFalse(state)
        self.assertEqual(fake_scheduler.calls, [])
        self.assertEqual(error_log.call_count, 1)

    def test_execute_received_task_does_not_log_success_when_submission_fails(self):
        fake_logger = _FakeLogger()
        task_data = {
            "function_code": "def demo_task():\n    return 'ok'\n",
            "function_name": "demo_task",
            "task_name": "demo-task",
            "task_id": "task-1",
        }

        with patch.object(core_module, "start_task_status_ui"), \
                patch.object(core_module, "logger", fake_logger), \
                patch.object(core_module, "task_submit", return_value=False) as task_submit:
            core = core_module.TaskServerCore()
            core.execute_received_task(task_data)

        self.assertEqual(task_submit.call_count, 1)
        self.assertEqual(len(fake_logger.info_calls), 0)

    def test_rpc_client_reads_control_port_from_config(self):
        with patch.dict(rpc_client_module.config, {
            "control_host": "127.0.0.1",
            "control_port": 8300,
            "control_ip": 9999,
        }, clear=False):
            client = rpc_client_module.RPCClient()

        self.assertEqual(client.host, "127.0.0.1")
        self.assertEqual(client.port, 8300)


if __name__ == "__main__":
    unittest.main()
