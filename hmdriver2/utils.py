# -*- coding: utf-8 -*-


import time
import socket
import re
from functools import wraps
from typing import Union

from .proto import Bounds


def delay(func):
    """
    After each UI operation, it is necessary to wait for a while to ensure the stability of the UI,
    so as not to affect the next UI operation.
    """
    DELAY_TIME = 0.6

    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        time.sleep(DELAY_TIME)
        return result
    return wrapper


class FreePort:
    def __init__(self):
        self._start = 10000
        self._end = 20000
        self._now = self._start - 1

    def get(self) -> int:
        while True:
            self._now += 1
            if self._now > self._end:
                self._now = self._start
            if not self.is_port_in_use(self._now):
                return self._now

    @staticmethod
    def is_port_in_use(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0


def parse_bounds(bounds: str) -> Union[Bounds, None]:
    """
    Parse bounds string to Bounds.
    bounds is str, like: "[832,1282][1125,1412]"
    """
    result = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
    if result:
        g = result.groups()
        return Bounds(int(g[0]),
                      int(g[1]),
                      int(g[2]),
                      int(g[3]))
    return None