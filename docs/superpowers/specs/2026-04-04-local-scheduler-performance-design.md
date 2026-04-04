# Local Scheduler Performance Design

## Goal

Optimize local single-machine scheduling throughput and idle overhead without changing the project's external API, task model, status model, or feature boundary.

## Scope

In scope:

- `task_scheduling/manager/scheduler_manager.py`
- `task_scheduling/scheduler/api.py`
- local scheduler internals in `task_scheduling/scheduler/`
- regression tests for unchanged behavior

Out of scope:

- RPC, proxy, result server, and Web UI behavior
- changing task priority semantics
- changing public configuration keys
- adding new runtime dependencies

## Problems Observed

1. `TaskScheduler.add_task()` increments `_task_counter` but never resets it, so after 40 submissions every new task can trigger `gc.collect()`. This directly hurts burst submit throughput.
2. Several schedulers rebuild `running_task_names` from `_running_tasks` during every `add_task()` call. This makes the hot add path scale with the number of currently running tasks.
3. `scheduler_manager._allocator()` and some scheduler loops use `empty()` plus follow-up queue operations and timeout-based waiting. This adds avoidable wakeups and can create unnecessary contention in idle and burst scenarios.
4. `cleanup_results_api()` copies whole result dictionaries before pruning. That adds avoidable allocation and lock time under result pressure.

## Chosen Approach

Use narrow internal optimizations only:

- make GC triggering periodic instead of permanently hot
- maintain running task names incrementally instead of rebuilding transient sets
- switch hot queue consumers to blocking/event-driven retrieval where possible
- prune result dictionaries in place under lock

This keeps all external behavior intact while reducing unnecessary work on the submit and idle paths.

## Safety Constraints

- task acceptance and rejection rules must remain unchanged
- same-name concurrency blocking must remain unchanged
- scheduler shutdown and idle timeout behavior must remain unchanged
- task status transitions must remain compatible with current consumers

## Validation

- add `unittest` coverage for the GC threshold fix
- add `unittest` coverage for same-name rejection without rebuilding transient sets
- add `unittest` coverage for allocator blocking behavior and cleanup thread single-start behavior where practical
- run the focused test module with `python -m unittest`
