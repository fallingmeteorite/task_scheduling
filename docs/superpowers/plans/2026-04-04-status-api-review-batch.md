# Status API Review Batch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Batch the remaining status-query review fixes into a single PR without changing scheduler capabilities.

**Architecture:** Add focused regression tests around the Web UI status query path, then make the smallest code changes needed to use the task status manager's thread-safe snapshot API and to degrade cleanly when clients disconnect during JSON responses. Keep the external payload shape unchanged.

**Tech Stack:** Python, `unittest`, existing Web UI/status modules

---

### Task 1: Add Regression Tests For Status Query Stability

**Files:**
- Create: `tests/test_status_api_review_batch.py`
- Modify: `task_scheduling/server_webui/ui.py`
- Modify: `docs/local/status_query.md`
- Modify: `docs/network/status_query.md`

- [ ] **Step 1: Write the failing test**

```python
class StatusApiReviewBatchTests(unittest.TestCase):
    def test_get_tasks_info_uses_status_manager_snapshot(self):
        ...

    def test_handle_tasks_ignores_broken_pipe(self):
        ...

    def test_handle_task_addition_status_ignores_broken_pipe(self):
        ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -p "test_status_api_review_batch.py" -v`
Expected: the snapshot test fails because `get_tasks_info()` reads `_task_status_dict` directly, and the HTTP handler tests fail because `BrokenPipeError` is not swallowed.

- [ ] **Step 3: Write minimal implementation**

```python
# ui.py
# Read task status through task_status_manager.get_all_task_statuses()
# Treat BrokenPipe/ConnectionReset on JSON status responses as normal disconnects.

# docs/local/status_query.md / docs/network/status_query.md
# Align get_tasks_info() return type with the actual structured payload.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -p "test_status_api_review_batch.py" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_status_api_review_batch.py task_scheduling/server_webui/ui.py docs/local/status_query.md docs/network/status_query.md docs/superpowers/plans/2026-04-04-status-api-review-batch.md
git commit -m "fix: harden status query api"
```
