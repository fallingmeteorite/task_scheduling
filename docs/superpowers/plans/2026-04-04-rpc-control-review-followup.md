# RPC Control Review Follow-Up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix RPC/control-layer bugs found in review without changing scheduler capabilities.

**Architecture:** Add focused regression tests around the public RPC client and Web UI startup entrypoint, then apply the smallest code changes needed to align those public APIs with the server-side implementation and documented arguments.

**Tech Stack:** Python, `unittest`, existing RPC/Web UI modules

---

### Task 1: Add Regression Tests For RPC And Web UI Entrypoints

**Files:**
- Create: `tests/test_rpc_control_review_followup.py`
- Modify: `task_scheduling/client/rpc_client.py`
- Modify: `task_scheduling/server_webui/ui.py`
- Modify: `docs/web_control.md`

- [ ] **Step 1: Write the failing test**

```python
class RpcControlReviewFollowupTests(unittest.TestCase):
    def test_rpc_client_get_task_count_forwards_task_name(self):
        ...

    def test_start_task_status_ui_applies_host_override(self):
        ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -p "test_rpc_control_review_followup.py" -v`
Expected: `get_task_count("task1")` raises because the method signature is wrong, and `start_task_status_ui(host=...)` ignores the provided host.

- [ ] **Step 3: Write minimal implementation**

```python
# rpc_client.py
# Make get_task_count accept task_name and forward it to the RPC server.

# ui.py
# Apply the caller-provided host override inside start_task_status_ui().

# docs/web_control.md
# Keep the public docs aligned with the corrected startup parameters.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -p "test_rpc_control_review_followup.py" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_rpc_control_review_followup.py task_scheduling/client/rpc_client.py task_scheduling/server_webui/ui.py docs/web_control.md docs/superpowers/plans/2026-04-04-rpc-control-review-followup.md
git commit -m "fix: align rpc control entrypoints"
```
