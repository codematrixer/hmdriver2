# -*- coding: utf-8 -*-

import math
from typing import List, Union, Optional, Tuple, Callable, Any

from . import logger
from .driver import Driver
from .exception import InjectGestureError
from .proto import HypiumResponse, Point
from .utils import delay

# 手势采样时间常量（毫秒）
SAMPLE_TIME_MIN = 10      # 最小采样时间
SAMPLE_TIME_NORMAL = 50   # 正常采样时间
SAMPLE_TIME_MAX = 100     # 最大采样时间

# 手势步骤类型常量
STEP_TYPE_START = "start"  # 开始手势
STEP_TYPE_MOVE = "move"    # 移动手势
STEP_TYPE_PAUSE = "pause"  # 暂停手势


class _Gesture:
    """
    手势操作类
    
    提供了创建和执行复杂手势操作的功能，包括点击、滑动、暂停等。
    通过链式调用可以组合多个手势步骤。
    """

    def __init__(self, d: Driver, sampling_ms: int = SAMPLE_TIME_NORMAL):
        """
        初始化手势对象
        
        Args:
            d: Driver 实例，用于与设备交互
            sampling_ms: 手势操作点的采样时间（毫秒），默认为 50
        """
        self.d = d
        self.steps: List[GestureStep] = []
        self.sampling_ms = self._validate_sampling_time(sampling_ms)

    def _validate_sampling_time(self, sampling_time: int) -> int:
        """
        验证采样时间是否在有效范围内
        
        Args:
            sampling_time: 给定的采样时间
            
        Returns:
            int: 有效范围内的采样时间
        """
        if SAMPLE_TIME_MIN <= sampling_time <= SAMPLE_TIME_MAX:
            return sampling_time
        return SAMPLE_TIME_NORMAL

    def _release(self) -> None:
        """清空手势步骤列表"""
        self.steps = []

    def start(self, x: Union[int, float], y: Union[int, float], interval: float = 0.5) -> '_Gesture':
        """
        开始手势操作
        
        Args:
            x: X 坐标，可以是百分比（0-1）或绝对值
            y: Y 坐标，可以是百分比（0-1）或绝对值
            interval: 在起始位置停留的时间（秒），默认为 0.5
            
        Returns:
            _Gesture: 当前实例，支持链式调用
            
        Raises:
            InjectGestureError: 手势已经开始时抛出
        """
        self._ensure_can_start()
        self._add_step(x, y, STEP_TYPE_START, interval)
        return self

    def move(self, x: Union[int, float], y: Union[int, float], interval: float = 0.5) -> '_Gesture':
        """
        移动到指定位置
        
        Args:
            x: X 坐标，可以是百分比（0-1）或绝对值
            y: Y 坐标，可以是百分比（0-1）或绝对值
            interval: 移动的持续时间（秒），默认为 0.5
            
        Returns:
            _Gesture: 当前实例，支持链式调用
            
        Raises:
            InjectGestureError: 手势未开始时抛出
        """
        self._ensure_started()
        self._add_step(x, y, STEP_TYPE_MOVE, interval)
        return self

    def pause(self, interval: float = 1) -> '_Gesture':
        """
        在当前位置暂停指定时间
        
        Args:
            interval: 暂停时间（秒），默认为 1
            
        Returns:
            _Gesture: 当前实例，支持链式调用
            
        Raises:
            InjectGestureError: 手势未开始时抛出
        """
        self._ensure_started()
        pos = self.steps[-1].pos
        self.steps.append(GestureStep(pos, STEP_TYPE_PAUSE, interval))
        return self

    @delay
    def action(self) -> None:
        """
        执行手势操作
        
        该方法会将所有已定义的手势步骤转换为触摸事件并发送到设备
        """
        logger.info(f">>>执行手势步骤: {self.steps}")
        total_points = self._calculate_total_points()

        pointer_matrix = self._create_pointer_matrix(total_points)
        self._generate_points(pointer_matrix, total_points)

        self._inject_pointer_actions(pointer_matrix)

        self._release()

    def _create_pointer_matrix(self, total_points: int) -> Any:
        """
        创建手势操作的指针矩阵
        
        Args:
            total_points: 总点数
            
        Returns:
            Any: 指针矩阵对象
        """
        fingers = 1  # 当前仅支持单指操作
        api = "PointerMatrix.create"
        data: HypiumResponse = self.d._client.invoke(api, this=None, args=[fingers, total_points])
        return data.result

    def _inject_pointer_actions(self, pointer_matrix: Any) -> None:
        """
        将指针操作注入到设备
        
        Args:
            pointer_matrix: 要注入的指针矩阵
        """
        api = "Driver.injectMultiPointerAction"
        self.d._client.invoke(api, args=[pointer_matrix, 2000])

    def _add_step(self, x: Union[int, float], y: Union[int, float], step_type: str, interval: float) -> None:
        """
        添加手势步骤
        
        Args:
            x: X 坐标
            y: Y 坐标
            step_type: 步骤类型（"start"、"move" 或 "pause"）
            interval: 时间间隔（秒）
        """
        point: Point = self.d._to_abs_pos(x, y)
        step = GestureStep(point.to_tuple(), step_type, interval)
        self.steps.append(step)

    def _ensure_can_start(self) -> None:
        """
        确保手势可以开始
        
        Raises:
            InjectGestureError: 手势已经开始时抛出
        """
        if self.steps:
            raise InjectGestureError("不能重复开始手势")

    def _ensure_started(self) -> None:
        """
        确保手势已经开始
        
        Raises:
            InjectGestureError: 手势未开始时抛出
        """
        if not self.steps:
            raise InjectGestureError("请先调用 gesture.start")

    def _generate_points(self, pointer_matrix: Any, total_points: int) -> None:
        """
        为指针矩阵生成点
        
        Args:
            pointer_matrix: 要填充的指针矩阵
            total_points: 要生成的总点数
        """
        # 定义设置点的内部函数
        def set_point(point_index: int, point: Point, interval: Optional[int] = None) -> None:
            """
            在指针矩阵中设置点
            
            Args:
                point_index: 点的索引
                point: 点对象
                interval: 时间间隔（可选）
            """
            if interval is not None:
                point.x += 65536 * interval
            api = "PointerMatrix.setPoint"
            self.d._client.invoke(api, this=pointer_matrix, args=[0, point_index, point.to_dict()])

        point_index = 0

        # 处理所有手势步骤
        for index, step in enumerate(self.steps):
            if step.type == STEP_TYPE_START:
                point_index = self._generate_start_point(step, point_index, set_point)
            elif step.type == STEP_TYPE_MOVE:
                point_index = self._generate_move_points(index, step, point_index, set_point)
            elif step.type == STEP_TYPE_PAUSE:
                point_index = self._generate_pause_points(step, point_index, set_point)

        # 填充剩余点
        step = self.steps[-1]
        while point_index < total_points:
            set_point(point_index, Point(*step.pos))
            point_index += 1

    def _generate_start_point(self, step: 'GestureStep', point_index: int,
                             set_point: Callable) -> int:
        """
        生成起始点
        
        Args:
            step: 手势步骤
            point_index: 当前点索引
            set_point: 设置点的函数
            
        Returns:
            int: 更新后的点索引
        """
        set_point(point_index, Point(*step.pos), step.interval)
        point_index += 1
        pos = step.pos[0], step.pos[1]
        set_point(point_index, Point(*pos))
        return point_index + 1

    def _generate_move_points(self, index: int, step: 'GestureStep',
                             point_index: int, set_point: Callable) -> int:
        """
        生成移动点
        
        Args:
            index: 步骤索引
            step: 手势步骤
            point_index: 当前点索引
            set_point: 设置点的函数
            
        Returns:
            int: 更新后的点索引
        """
        last_step = self.steps[index - 1]
        offset_x = step.pos[0] - last_step.pos[0]
        offset_y = step.pos[1] - last_step.pos[1]
        distance = int(math.sqrt(offset_x ** 2 + offset_y ** 2))
        interval_ms = step.interval
        cur_steps = self._calculate_move_step_points(distance, interval_ms)

        # 避免除零错误
        if cur_steps <= 0:
            cur_steps = 1

        step_x = int(offset_x / cur_steps)
        step_y = int(offset_y / cur_steps)

        set_point(point_index - 1, Point(*last_step.pos), self.sampling_ms)
        x, y = last_step.pos[0], last_step.pos[1]
        for _ in range(cur_steps):
            x += step_x
            y += step_y
            set_point(point_index, Point(x, y), self.sampling_ms)
            point_index += 1
        return point_index

    def _generate_pause_points(self, step: 'GestureStep', point_index: int,
                              set_point: Callable) -> int:
        """
        生成暂停点
        
        Args:
            step: 手势步骤
            point_index: 当前点索引
            set_point: 设置点的函数
            
        Returns:
            int: 更新后的点索引
        """
        # 计算需要的点数
        points = max(1, int(step.interval / self.sampling_ms))
        for _ in range(points):
            set_point(point_index, Point(*step.pos), int(step.interval / points))
            point_index += 1
        pos = step.pos[0] + 3, step.pos[1]  # 微小移动以触发事件
        set_point(point_index, Point(*pos))
        return point_index + 1

    def _calculate_total_points(self) -> int:
        """
        计算手势所需的总点数
        
        Returns:
            int: 总点数
        """
        total_points = 0
        for index, step in enumerate(self.steps):
            if step.type == STEP_TYPE_START:
                total_points += 2
            elif step.type == STEP_TYPE_MOVE:
                distance, interval_ms = self._calculate_move_distance(step, index)
                total_points += self._calculate_move_step_points(distance, interval_ms)
            elif step.type == STEP_TYPE_PAUSE:
                points = max(1, int(step.interval / self.sampling_ms))
                total_points += points + 1
        return total_points

    def _calculate_move_distance(self, step: 'GestureStep', index: int) -> Tuple[int, float]:
        """
        计算移动距离和时间间隔
        
        Args:
            step: 手势步骤
            index: 步骤索引
            
        Returns:
            Tuple[int, float]: (距离, 时间间隔(毫秒))
        """
        last_step = self.steps[index - 1]
        offset_x = step.pos[0] - last_step.pos[0]
        offset_y = step.pos[1] - last_step.pos[1]
        distance = int(math.sqrt(offset_x ** 2 + offset_y ** 2))
        interval_ms = step.interval
        return distance, interval_ms

    def _calculate_move_step_points(self, distance: int, interval_ms: float) -> int:
        """
        根据距离和时间计算移动步骤点数
        
        Args:
            distance: 移动距离
            interval_ms: 移动持续时间（毫秒）
            
        Returns:
            int: 移动步骤点数
        """
        if interval_ms < self.sampling_ms or distance < 1:
            return 1
        nums = interval_ms / self.sampling_ms
        return min(distance, int(nums))


class GestureStep:
    """
    手势步骤类
    
    存储手势的每个步骤，不直接使用，通过 Gesture 类使用
    """

    def __init__(self, pos: Tuple[int, int], step_type: str, interval: float):
        """
        初始化手势步骤
        
        Args:
            pos: 包含 x 和 y 坐标的元组
            step_type: 步骤类型（"start"、"move"、"pause"）
            interval: 时间间隔（秒）
        """
        self.pos = pos[0], pos[1]
        self.interval = int(interval * 1000)  # 转换为毫秒
        self.type = step_type

    def __repr__(self) -> str:
        """返回手势步骤的字符串表示"""
        return f"GestureStep(pos=({self.pos[0]}, {self.pos[1]}), type='{self.type}', interval={self.interval})"

    def __str__(self) -> str:
        """返回手势步骤的字符串表示"""
        return self.__repr__()