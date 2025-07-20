# -*- coding: utf-8 -*-
from .is_async_function import is_async_function
from .sleep import interruptible_sleep
# Used for task tagging
from .worker_initializer import worker_initializer_liner, worker_initializer_asyncio
from .random_name import random_name