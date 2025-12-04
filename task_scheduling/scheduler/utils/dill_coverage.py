# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Dill-enabled process pool executor module.

This module provides a ProcessPoolExecutor subclass that uses dill for
serialization, enabling the execution of functions and classes that
are not pickleable by default.
"""

import concurrent.futures
import multiprocessing

import dill


class DillProcessPoolExecutor(concurrent.futures.ProcessPoolExecutor):
    """Process pool executor that uses dill for serialization.

    This class extends ProcessPoolExecutor to replace the default pickle
    serializer with dill, allowing serialization of more complex Python
    objects including lambda functions, nested functions, and local classes.

    Args:
        max_workers: Maximum number of worker processes.
        initializer: Callable used to initialize worker processes.
        initargs: Arguments passed to the initializer.
        mp_context: Multiprocessing context or context string.
        **kwargs: Additional keyword arguments passed to parent class.
    """

    def __init__(self, max_workers=None, initializer=None, initargs=(),
                 mp_context=None, **kwargs):
        """Initialize the DillProcessPoolExecutor.

        Ensures the use of 'spawn' context by default and patches the
        multiprocessing serializer to use dill.
        """
        # Make sure to use the spawn context
        if mp_context is None:
            mp_context = multiprocessing.get_context('spawn')
        elif isinstance(mp_context, str):
            mp_context = multiprocessing.get_context(mp_context)

        # Replace the serializer with dill
        self._patch_serializer(mp_context)

        super().__init__(
            max_workers=max_workers,
            initializer=initializer,
            initargs=initargs,
            mp_context=mp_context,
            **kwargs
        )

    def _patch_serializer(self, mp_context):
        """Replace the serializer for multiprocessing with dill"""

        def dill_dumps(obj, protocol=None):
            return dill.dumps(obj, protocol=protocol, recurse=True)

        multiprocessing.connection._ForkingPickler.dumps = dill_dumps
