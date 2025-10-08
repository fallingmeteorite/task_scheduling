# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import uuid

def random_name(prefix:str) -> str:
    return f"{prefix}{str(uuid.uuid4())}"
