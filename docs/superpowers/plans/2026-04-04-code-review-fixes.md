# Code Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix real behavior bugs found during code review without expanding the project's capability boundary.

**Architecture:** Add focused regression tests around the scheduler status and priority handoff behavior, then make the smallest code changes needed in the existing scheduler implementations. Keep all fixes inside the current scheduling model and avoid API redesign.

**Tech Stack:** Python, `unittest`, existing scheduler modules

---

### Task 1: Add Regression Tests For Review Findings

**Files:**
- Create: `tests/test_code_review_fixes.py`
- Modify: `task_scheduling/scheduler/io_liner_task.py`
- Modify: `task_scheduling/scheduler/cpu_liner_task.py`
- Modify: `task_scheduling/scheduler/timer_task.py`

- [ ] **Step 1: Write the failing test**

```python
class CodeReviewFixTests(unittest.TestCase):
    def test_io_linear_high_priority_task_can_preempt_when_full(self):
        ...

    def test_cpu_linear_high_priority_task_can_preempt_when_full(self):
        ...

    def test_timer_resume_uses_timer_task_type(self):
        ...

    def test_io_linear_done_marks_unhandled_errors_as_failed(self):
        ...

    def test_timer_done_marks_unhandled_errors_as_failed(self):
        ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_code_review_fixes -v`
Expected: high priority insertion test fails, timer resume task type test fails, and failed/cancelled status tests fail.

- [ ] **Step 3: Write minimal implementation**

```python
# io_liner_task.py / cpu_liner_task.py
# Only reject full schedulers when the task is not eligible for high-priority preemption.

# timer_task.py
# Report resume status with task_type="timer_task"
# Report unexpected future exceptions as status="failed"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_code_review_fixes -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_code_review_fixes.py task_scheduling/scheduler/io_liner_task.py task_scheduling/scheduler/cpu_liner_task.py task_scheduling/scheduler/timer_task.py docs/superpowers/plans/2026-04-04-code-review-fixes.md
git commit -m "fix: correct scheduler review regressions"
```
