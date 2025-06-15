# -*- coding: utf-8 -*-

from typing import Union, Tuple, Optional, Literal

from .driver import Driver
from .proto import SwipeDirection, Point


# 滑动方向的字符串类型
SwipeDirectionStr = Literal["left", "right", "up", "down"]

# 默认滑动速度（像素/秒）
DEFAULT_SWIPE_SPEED = 2000
# 速度限制
MIN_SWIPE_SPEED = 200
MAX_SWIPE_SPEED = 40000


class SwipeExt:
    """
    扩展滑动功能类
    
    提供了更灵活的滑动操作，支持方向、比例和区域定制
    """
    
    def __init__(self, d: Driver):
        """
        初始化滑动扩展功能
        
        Args:
            d: Driver 实例
        """
        self._d = d

    def __call__(
        self,
        direction: Union[SwipeDirection, SwipeDirectionStr],
        scale: float = 0.8,
        box: Optional[Tuple[int, int, int, int]] = None,
        speed: int = DEFAULT_SWIPE_SPEED
    ) -> None:
        """
        执行滑动操作
        
        Args:
            direction: 滑动方向，可以是 "left", "right", "up", "down" 或 SwipeDirection 枚举
            scale: 滑动比例，范围 (0, 1.0]，表示滑动距离占可滑动区域的比例
            box: 滑动区域，格式为 (x1, y1, x2, y2)，默认为全屏
            speed: 滑动速度（像素/秒），默认为 2000，有效范围 200-40000
            
        Raises:
            ValueError: 参数无效时抛出
        """
        def _swipe(_from: Tuple[int, int], _to: Tuple[int, int]) -> None:
            """执行从一点到另一点的滑动"""
            self._d.swipe(_from[0], _from[1], _to[0], _to[1], speed=speed)

        # 验证 scale 参数
        if scale <= 0 or scale > 1.0 or not isinstance(scale, (float, int)):
            raise ValueError("scale must be in range (0, 1.0]")

        # 验证 speed 参数
        if speed < MIN_SWIPE_SPEED or speed > MAX_SWIPE_SPEED:
            speed = DEFAULT_SWIPE_SPEED

        # 确定滑动区域
        if box:
            x1, y1, x2, y2 = self._validate_and_convert_box(box)
        else:
            x1, y1 = 0, 0
            x2, y2 = self._d.display_size

        width, height = x2 - x1, y2 - y1

        # 计算偏移量，确保滑动在边缘留有间距
        h_offset = int(width * (1 - scale) / 2)
        v_offset = int(height * (1 - scale) / 2)

        # 根据方向确定滑动的起点和终点
        if direction in [SwipeDirection.LEFT, "left"]:
            start = (x2 - h_offset, y1 + height // 2)
            end = (x1 + h_offset, y1 + height // 2)
        elif direction in [SwipeDirection.RIGHT, "right"]:
            start = (x1 + h_offset, y1 + height // 2)
            end = (x2 - h_offset, y1 + height // 2)
        elif direction in [SwipeDirection.UP, "up"]:
            start = (x1 + width // 2, y2 - v_offset)
            end = (x1 + width // 2, y1 + v_offset)
        elif direction in [SwipeDirection.DOWN, "down"]:
            start = (x1 + width // 2, y1 + v_offset)
            end = (x1 + width // 2, y2 - v_offset)
        else:
            raise ValueError(f"Unknown SwipeDirection: {direction}")

        # 执行滑动
        _swipe(start, end)

    def _validate_and_convert_box(self, box: Tuple) -> Tuple[int, int, int, int]:
        """
        验证并转换区域坐标
        
        Args:
            box: 区域坐标元组 (x1, y1, x2, y2)
            
        Returns:
            Tuple[int, int, int, int]: 验证并转换后的区域坐标
            
        Raises:
            ValueError: 坐标无效时抛出
        """
        # 验证元组长度
        if not isinstance(box, tuple) or len(box) != 4:
            raise ValueError("Box must be a tuple of length 4.")
        
        x1, y1, x2, y2 = box
        
        # 验证坐标值
        if not all(isinstance(coord, (int, float)) for coord in box):
            raise ValueError("All coordinates must be numeric.")
            
        # 验证坐标范围
        if not (x1 >= 0 and y1 >= 0 and x2 > 0 and y2 > 0):
            raise ValueError("Box coordinates must be greater than 0.")
            
        # 验证坐标关系
        if not (x1 < x2 and y1 < y2):
            raise ValueError("Box coordinates must satisfy x1 < x2 and y1 < y2.")

        # 转换坐标到绝对位置
        p1: Point = self._d._to_abs_pos(x1, y1)
        p2: Point = self._d._to_abs_pos(x2, y2)
        return p1.x, p1.y, p2.x, p2.y
