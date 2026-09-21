# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Thread and process creation restriction module.

This module provides a mechanism to restrict thread and process creation
inside designated worker threads. The restriction scope accepts parameters
to selectively block thread creation, process creation, subprocess spawning,
or any combination of them.
"""
import os
import _thread
import threading
from typing import Any, Optional, Set, FrozenSet

# Valid restriction categories
_RESTRICT_THREAD = "thread"
_RESTRICT_PROCESS = "process"
_RESTRICT_SUBPROCESS = "subprocess"
_RESTRICT_ALL = "all"

_VALID_CATEGORIES: FrozenSet[str] = frozenset({
    _RESTRICT_THREAD,
    _RESTRICT_PROCESS,
    _RESTRICT_SUBPROCESS,
})

# Thread-local storage for the set of blocked categories
_restricted = threading.local()


class ThreadRestrictionError(RuntimeError):
    """
    Raised when a restricted thread attempts to create threads or processes.
    """
    pass


def _normalize_categories(categories: tuple) -> FrozenSet[str]:
    """
    Normalize user-provided categories into a frozenset.

    Args:
        categories: Variable-length category names. If empty, defaults to
            all categories. "all" expands to every supported category.

    Returns:
        A frozenset of normalized category names.

    Raises:
        ValueError: If an unknown category name is provided.
    """
    if not categories:
        return _VALID_CATEGORIES

    normalized: Set[str] = set()
    for category in categories:
        if category == _RESTRICT_ALL:
            normalized.update(_VALID_CATEGORIES)
        elif category in _VALID_CATEGORIES:
            normalized.add(category)
        else:
            raise ValueError(
                f"unknown restrict category | {category} |, "
                f"valid categories are: {sorted(_VALID_CATEGORIES)} or 'all'"
            )
    return frozenset(normalized)


def _current_blocked() -> FrozenSet[str]:
    """
    Get the set of currently blocked categories in the current thread.

    Returns:
        A frozenset of blocked category names, empty if unrestricted.
    """
    return getattr(_restricted, "blocked", frozenset())


def is_blocked(category: str) -> bool:
    """
    Check whether a specific category is blocked in the current thread.

    Args:
        category: The category to check, one of "thread", "process",
            "subprocess".

    Returns:
        True if the category is blocked, False otherwise.
    """
    return category in _current_blocked()


def is_restricted() -> bool:
    """
    Check whether the current thread is restricted in any way.

    Returns:
        True if any category is blocked, False otherwise.
    """
    return bool(_current_blocked())


class RestrictScope:
    """
    Context manager that marks the current thread with blocked categories.

    Nested usage is safe: inner scopes take the union with outer scopes,
    so a scope can only become stricter, never looser.
    """
    __slots__ = ["_previous", "_categories"]

    def __init__(self, *categories: str) -> None:
        """
        Initialize the restrict scope.

        Args:
            *categories: Categories to block. Accepts "thread", "process",
                "subprocess", or "all". If omitted, all categories are blocked.
        """
        self._categories = _normalize_categories(categories)
        self._previous: FrozenSet[str] = frozenset()

    def __enter__(self) -> "RestrictScope":
        """
        Enter the restricted scope and merge blocked categories.

        Returns:
            The RestrictScope instance itself.
        """
        self._previous = _current_blocked()
        # Inner scope can only strengthen, never weaken
        _restricted.blocked = self._previous | self._categories
        return self

    def __exit__(self,
                 exc_type: Optional[type],
                 exc_val: Optional[BaseException],
                 exc_tb: Optional[Any]) -> bool:
        """
        Exit the restricted scope and restore the previous blocked set.

        Args:
            exc_type: Exception type if an exception was raised.
            exc_val: Exception value if an exception was raised.
            exc_tb: Exception traceback if an exception was raised.

        Returns:
            False to propagate any exception.
        """
        _restricted.blocked = self._previous
        return False


def _patch_thread_start() -> None:
    """
    Patch threading.Thread.start to block restricted thread creation.
    """
    _original_start = threading.Thread.start

    def _guarded_start(self) -> None:
        if is_blocked(_RESTRICT_THREAD):
            raise ThreadRestrictionError(
                f"thread | {threading.current_thread().name} | "
                f"is restricted and cannot create thread | {self.name} |"
            )
        return _original_start(self)

    threading.Thread.start = _guarded_start


def _patch_thread_low_level() -> None:
    """
    Patch _thread.start_new_thread to block restricted low-level thread creation.
    """
    _original_start_new = _thread.start_new_thread

    def _guarded_start_new(function: Any, args: tuple, kwargs: Optional[dict] = None) -> Any:
        if is_blocked(_RESTRICT_THREAD):
            raise ThreadRestrictionError(
                f"thread | {threading.current_thread().name} | "
                f"is restricted and cannot call _thread.start_new_thread"
            )
        return _original_start_new(function, args, kwargs)

    _thread.start_new_thread = _guarded_start_new
    if hasattr(_thread, "start_new"):
        _thread.start_new = _guarded_start_new


def _patch_thread_pool_executor() -> None:
    """
    Patch ThreadPoolExecutor.submit to block restricted thread pool usage.
    """
    try:
        from concurrent.futures import ThreadPoolExecutor

        _original_submit = ThreadPoolExecutor.submit

        def _guarded_submit(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
            if is_blocked(_RESTRICT_THREAD):
                raise ThreadRestrictionError(
                    f"thread | {threading.current_thread().name} | "
                    f"is restricted and cannot use ThreadPoolExecutor"
                )
            return _original_submit(self, fn, *args, **kwargs)

        ThreadPoolExecutor.submit = _guarded_submit
    except ImportError:
        pass


def _patch_process() -> None:
    """
    Patch multiprocessing.Process.start to block restricted process creation.
    """
    try:
        import multiprocessing

        _original_start = multiprocessing.Process.start

        def _guarded_start(self) -> Any:
            if is_blocked(_RESTRICT_PROCESS):
                raise ThreadRestrictionError(
                    f"thread | {threading.current_thread().name} | "
                    f"is restricted and cannot create process"
                )
            return _original_start(self)

        multiprocessing.Process.start = _guarded_start
    except ImportError:
        pass


def _patch_process_pool_executor() -> None:
    """
    Patch ProcessPoolExecutor.submit to block restricted process pool usage.
    """
    try:
        from concurrent.futures import ProcessPoolExecutor

        _original_submit = ProcessPoolExecutor.submit

        def _guarded_submit(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
            if is_blocked(_RESTRICT_PROCESS):
                raise ThreadRestrictionError(
                    f"thread | {threading.current_thread().name} | "
                    f"is restricted and cannot use ProcessPoolExecutor"
                )
            return _original_submit(self, fn, *args, **kwargs)

        ProcessPoolExecutor.submit = _guarded_submit
    except ImportError:
        pass


def _patch_fork() -> None:
    """
    Patch os.fork to block restricted fork calls.
    """
    if not hasattr(os, "fork"):
        return None

    _original_fork = os.fork

    def _guarded_fork() -> int:
        if is_blocked(_RESTRICT_PROCESS):
            raise ThreadRestrictionError(
                f"thread | {threading.current_thread().name} | "
                f"is restricted and cannot fork"
            )
        return _original_fork()

    os.fork = _guarded_fork
    return None


def _patch_subprocess() -> None:
    """
    Patch subprocess.Popen to block restricted subprocess creation.
    """
    try:
        import subprocess

        _original_init = subprocess.Popen.__init__

        def _guarded_init(self, *args: Any, **kwargs: Any) -> None:
            if is_blocked(_RESTRICT_SUBPROCESS):
                raise ThreadRestrictionError(
                    f"thread | {threading.current_thread().name} | "
                    f"is restricted and cannot spawn subprocess"
                )
            return _original_init(self, *args, **kwargs)

        subprocess.Popen.__init__ = _guarded_init
    except ImportError:
        pass


def install_patches() -> None:
    """
    Install all restriction patches.

    This function is called once at module import time. It patches all
    known thread and process creation entry points so that they respect
    the restriction flag.
    """
    _patch_thread_start()
    _patch_thread_low_level()
    _patch_thread_pool_executor()
    _patch_process()
    _patch_process_pool_executor()
    _patch_fork()
    _patch_subprocess()


# Install patches immediately upon import
install_patches()


# Public alias with snake_case to match the import in io_liner_task.py
restrict_scope = RestrictScope