import sys
import types
import unittest
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
        UnpicklingError=ValueError,
    )

if "loguru" not in sys.modules:
    sys.modules["loguru"] = types.SimpleNamespace(logger=_FakeLogger())

from task_scheduling.common import ensure_config_loaded

ensure_config_loaded()

import task_scheduling.client.rpc_client as rpc_client_module
import task_scheduling.server_webui.ui as webui_module


class RpcControlReviewFollowupTests(unittest.TestCase):
    def test_rpc_client_get_task_count_forwards_task_name(self):
        with patch.dict(rpc_client_module.config, {
            "control_host": "127.0.0.1",
            "control_ip": 8300,
        }, clear=False), \
                patch.object(rpc_client_module.RPCClient, "_rpc_call", return_value=2) as rpc_call:
            client = rpc_client_module.RPCClient()
            result = client.get_task_count("task1")

        self.assertEqual(result, 2)
        rpc_call.assert_called_once_with("get_task_count", "task1")

    def test_start_task_status_ui_applies_host_override(self):
        with patch.object(webui_module.TaskStatusServer, "start"):
            server = webui_module.start_task_status_ui(host="0.0.0.0", port=8123, max_port_attempts=12)

        self.assertEqual(server.host, "0.0.0.0")
        self.assertEqual(server.port, 8123)
        self.assertEqual(server.max_port_attempts, 12)


if __name__ == "__main__":
    unittest.main()
