# Client Network Review Follow-Up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix client and network entrypoint issues found during code review without expanding the scheduler capability boundary.

**Architecture:** Add focused regression tests around invalid `function_type` handling and RPC client configuration, then make the smallest code changes needed to reject unsupported task types early and align public documentation with the real API. Keep scheduler behavior for valid inputs unchanged.

**Tech Stack:** Python, `unittest`, existing client/server/task modules

---

### Task 1: Add Regression Tests For Client And Network Entry Points

**Files:**
- Create: `tests/test_client_network_review_followup.py`
- Modify: `task_scheduling/task_creation.py`
- Modify: `task_scheduling/main_server/utils/core.py`
- Modify: `task_scheduling/client/rpc_client.py`
- Modify: `task_scheduling/client/submit.py`
- Modify: `docs/local/task_disabling.md`
- Modify: `docs/network/task_disabling.md`

- [ ] **Step 1: Write the failing test**

```python
class ClientNetworkReviewFollowupTests(unittest.TestCase):
    def test_task_creation_rejects_unsupported_function_type(self):
        ...

    def test_network_task_submit_rejects_unsupported_function_type(self):
        ...

    def test_execute_received_task_does_not_log_success_when_submission_fails(self):
        ...

    def test_rpc_client_reads_control_port_from_config(self):
        ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -p "test_client_network_review_followup.py" -v`
Expected: invalid `function_type` tests fail and RPC client config test fails because it reads `control_ip`.

- [ ] **Step 3: Write minimal implementation**

```python
# Reject unsupported function_type values at local and network submission entrypoints.
# Only log network submission success when scheduling really succeeds.
# Read RPC client port from config["control_port"].
# Update public docstrings and task-disabling docs to match actual values/status names.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -p "test_client_network_review_followup.py" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_client_network_review_followup.py task_scheduling/task_creation.py task_scheduling/main_server/utils/core.py task_scheduling/client/rpc_client.py task_scheduling/client/submit.py docs/local/task_disabling.md docs/network/task_disabling.md docs/superpowers/plans/2026-04-04-client-network-review-followup.md
git commit -m "fix: harden client and network task validation"
```
