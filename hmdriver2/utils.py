# -*- coding: utf-8 -*-


import time
import socket
from functools import wraps


def delay(func):
    """
    After each UI operation, it is necessary to wait for a while to ensure the stability of the UI,
    so as not to affect the next UI operation.
    """
    DELAY_TIME = 0.5

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