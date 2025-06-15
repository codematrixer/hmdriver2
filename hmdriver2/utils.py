# -*- coding: utf-8 -*-

import re
import socket
import time
from functools import wraps
from typing import Optional, Callable, Any, TypeVar

from .proto import Bounds

# 默认 UI 操作后的延迟时间（秒）
DEFAULT_DELAY_TIME = 0.6

# 端口范围
PORT_RANGE_START = 10000
PORT_RANGE_END = 20000

# 类型变量定义，用于泛型函数
F = TypeVar('F', bound=Callable[..., Any])


def delay(func: F) -> F:
    """
    UI 操作后的延迟装饰器
    
    在每次 UI 操作后需要等待一段时间，确保 UI 稳定，
    避免影响下一次 UI 操作。
    
    Args:
        func: 要装饰的函数
        
    Returns:
        装饰后的函数
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = func(*args, **kwargs)
        time.sleep(DEFAULT_DELAY_TIME)
        return result

    return wrapper  # type: ignore


class FreePort:
    """
    空闲端口管理类
    
    用于获取系统中未被占用的网络端口
    """
    
    def __init__(self) -> None:
        """初始化端口管理器"""
        self._start = PORT_RANGE_START
        self._end = PORT_RANGE_END
        self._now = self._start - 1

    def get(self) -> int:
        """
        获取一个空闲端口
        
        Returns:
            int: 可用的端口号
        """
        attempts = 0
        max_attempts = self._end - self._start
        
        while attempts < max_attempts:
            attempts += 1
            self._now += 1
            if self._now > self._end:
                self._now = self._start
                
            if not self.is_port_in_use(self._now):
                return self._now
                
        raise RuntimeError(f"无法找到可用端口，已尝试 {max_attempts} 次")

    @staticmethod
    def is_port_in_use(port: int) -> bool:
        """
        检查端口是否被占用
        
        Args:
            port: 要检查的端口号
            
        Returns:
            bool: 端口被占用返回 True，否则返回 False
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('localhost', port)) == 0
        except (socket.error, OSError):
            # 如果发生错误，保守地认为端口被占用
            return True


def parse_bounds(bounds: str) -> Optional[Bounds]:
    """
    解析边界字符串为 Bounds 对象
    
    Args:
        bounds: 边界字符串，格式如 "[832,1282][1125,1412]"
        
    Returns:
        Optional[Bounds]: 解析成功返回 Bounds 对象，否则返回 None
    """
    if not bounds:
        return None
        
    result = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
    if result:
        g = result.groups()
        try:
            return Bounds(int(g[0]),
                          int(g[1]),
                          int(g[2]),
                          int(g[3]))
        except (ValueError, IndexError):
            return None
    return None
