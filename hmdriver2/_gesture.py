# -*- coding: utf-8 -*-

import math
from typing import List, Union
from . import logger
from .utils import delay
from .driver import Driver
from .proto import HypiumResponse, Point
from .exception import InjectGestureError


class _Gesture:
    SAMPLE_TIME_MIN = 10
    SAMPLE_TIME_NORMAL = 50
    SAMPLE_TIME_MAX = 100

    def __init__(self, driver: Driver, sampling_ms=50):
        """
        Initialize a gesture object.

        Args:
            driver (Driver): The driver object to interact with.
            sampling_ms (int): Sampling time for gesture operation points in milliseconds. Default is 50.
        """
        self.driver = driver
        self.steps: List[GestureStep] = []
        self.sampling_ms = self._validate_sampling_time(sampling_ms)

    def _validate_sampling_time(self, sampling_time: int) -> int:
        """
        Validate the input sampling time.

        Args:
            sampling_time (int): The given sampling time.

        Returns:
            int: Valid sampling time within allowed range.
        """
        if _Gesture.SAMPLE_TIME_MIN <= sampling_time <= _Gesture.SAMPLE_TIME_MAX:
            return sampling_time
        return _Gesture.SAMPLE_TIME_NORMAL

    def _release(self):
        self.steps = []

    def start(self, x: Union[int, float], y: Union[int, float], interval: float = 0.5) -> '_Gesture':
        """
        Start gesture operation.

        Args:
            x: oordinate as a percentage or absolute value.
            y: coordinate as a percentage or absolute value.
            interval (float, optional): Duration to hold at start position in seconds. Default is 0.5.

        Returns:
            Gesture: Self instance to allow method chaining.
        """
        self._ensure_can_start()
        self._add_step(x, y, "start", interval)
        return self

    def move(self, x: Union[int, float], y: Union[int, float], interval: float = 0.5) -> '_Gesture':
        """
        Move to specified position.

        Args:
            x: coordinate as a percentage or absolute value.
            y: coordinate as a percentage or absolute value.
            interval (float, optional): Duration of move in seconds. Default is 0.5.

        Returns:
            Gesture: Self instance to allow method chaining.
        """
        self._ensure_started()
        self._add_step(x, y, "move", interval)
        return self

    def pause(self, interval: float = 1) -> '_Gesture':
        """
        Pause at current position for specified duration.

        Args:
            interval (float, optional): Duration to pause in seconds. Default is 1.

        Returns:
            Gesture: Self instance to allow method chaining.
        """
        self._ensure_started()
        pos = self.steps[-1].pos
        self.steps.append(GestureStep(pos, "pause", interval))
        return self

    @delay
    def action(self):
        """
        Execute the gesture action.
        """
        logger.info(f">>>Gesture steps: {self.steps}")
        total_points = self._calculate_total_points()

        pointer_matrix = self._create_pointer_matrix(total_points)
        self._generate_points(pointer_matrix, total_points)

        self._inject_pointer_actions(pointer_matrix)

        self._release()

    def _create_pointer_matrix(self, total_points: int):
        """
        Create a pointer matrix for the gesture.

        Args:
            total_points (int): Total number of points.

        Returns:
            PointerMatrix: Pointer matrix object.
        """
        fingers = 1
        api = "PointerMatrix.create"
        data: HypiumResponse = self.driver._client.invoke(api, this=None, args=[fingers, total_points])
        return data.result

    def _inject_pointer_actions(self, pointer_matrix):
        """
        Inject pointer actions into the driver.

        Args:
            pointer_matrix (PointerMatrix): Pointer matrix to inject.
        """
        api = "Driver.injectMultiPointerAction"
        self.driver._client.invoke(api, args=[pointer_matrix, 2000])

    def _add_step(self, x: int, y: int, step_type: str, interval: float):
        """
        Add a step to the gesture.

        Args:
            x (int): x-coordinate of the point.
            y (int): y-coordinate of the point.
            step_type (str): Type of step ("start", "move", or "pause").
            interval (float): Interval duration in seconds.
        """
        point: Point = self.driver._to_abs_pos(x, y)
        step = GestureStep(point.to_tuple(), step_type, interval)
        self.steps.append(step)

    def _ensure_can_start(self):
        """
        Ensure that the gesture can start.
        """
        if self.steps:
            raise InjectGestureError("Can't start gesture twice")

    def _ensure_started(self):
        """
        Ensure that the gesture has started.
        """
        if not self.steps:
            raise InjectGestureError("Please call gesture.start first")

    def _generate_points(self, pointer_matrix, total_points):
        """
        Generate points for the pointer matrix.

        Args:
            pointer_matrix (PointerMatrix): Pointer matrix to populate.
            total_points (int): Total points to generate.
        """

        def set_point(point_index: int, point: Point, interval: int = None):
            """
            Set a point in the pointer matrix.

            Args:
                point_index (int): Index of the point.
                point (Point): The point object.
                interval (int, optional): Interval duration.
            """
            if interval is not None:
                point.x += 65536 * interval
            api = "PointerMatrix.setPoint"
            self.driver._client.invoke(api, this=pointer_matrix, args=[0, point_index, point.to_dict()])

        point_index = 0

        for index, step in enumerate(self.steps):
            if step.type == "start":
                point_index = self._generate_start_point(step, point_index, set_point)
            elif step.type == "move":
                point_index = self._generate_move_points(index, step, point_index, set_point)
            elif step.type == "pause":
                point_index = self._generate_pause_points(step, point_index, set_point)

        step = self.steps[-1]
        while point_index < total_points:
            set_point(point_index, Point(*step.pos))
            point_index += 1

    def _generate_start_point(self, step, point_index, set_point):
        """
        Generate start points.

        Args:
            step (GestureStep): Gesture step.
            point_index (int): Current point index.
            set_point (function): Function to set the point in pointer matrix.

        Returns:
            int: Updated point index.
        """
        set_point(point_index, Point(*step.pos), step.interval)
        point_index += 1
        pos = step.pos[0], step.pos[1]
        set_point(point_index, Point(*pos))
        return point_index + 1

    def _generate_move_points(self, index, step, point_index, set_point):
        """
        Generate move points.

        Args:
            index (int): Step index.
            step (GestureStep): Gesture step.
            point_index (int): Current point index.
            set_point (function): Function to set the point in pointer matrix.

        Returns:
            int: Updated point index.
        """
        last_step = self.steps[index - 1]
        offset_x = step.pos[0] - last_step.pos[0]
        offset_y = step.pos[1] - last_step.pos[1]
        distance = int(math.sqrt(offset_x ** 2 + offset_y ** 2))
        interval_ms = step.interval
        cur_steps = self._calculate_move_step_points(distance, interval_ms)

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

    def _generate_pause_points(self, step, point_index, set_point):
        """
        Generate pause points.

        Args:
            step (GestureStep): Gesture step.
            point_index (int): Current point index.
            set_point (function): Function to set the point in pointer matrix.

        Returns:
            int: Updated point index.
        """
        points = int(step.interval / self.sampling_ms)
        for _ in range(points):
            set_point(point_index, Point(*step.pos), int(step.interval / self.sampling_ms))
            point_index += 1
        pos = step.pos[0] + 3, step.pos[1]
        set_point(point_index, Point(*pos))
        return point_index + 1

    def _calculate_total_points(self) -> int:
        """
        Calculate the total number of points needed for the gesture.

        Returns:
            int: Total points.
        """
        total_points = 0
        for index, step in enumerate(self.steps):
            if step.type == "start":
                total_points += 2
            elif step.type == "move":
                total_points += self._calculate_move_step_points(
                    *self._calculate_move_distance(step, index))
            elif step.type == "pause":
                points = int(step.interval / self.sampling_ms)
                total_points += points + 1
        return total_points

    def _calculate_move_distance(self, step, index):
        """
        Calculate move distance and interval.

        Args:
            step (GestureStep): Gesture step.
            index (int): Step index.

        Returns:
            tuple: Tuple (distance, interval_ms).
        """
        last_step = self.steps[index - 1]
        offset_x = step.pos[0] - last_step.pos[0]
        offset_y = step.pos[1] - last_step.pos[1]
        distance = int(math.sqrt(offset_x ** 2 + offset_y ** 2))
        interval_ms = step.interval
        return distance, interval_ms

    def _calculate_move_step_points(self, distance: int, interval_ms: float) -> int:
        """
        Calculate the number of move step points based on distance and time.

        Args:
            distance (int): Distance to move.
            interval_ms (float): Move duration in milliseconds.

        Returns:
            int: Number of move step points.
        """
        if interval_ms < self.sampling_ms or distance < 1:
            return 1
        nums = interval_ms / self.sampling_ms
        return distance if nums > distance else int(nums)


class GestureStep:
    """Class to store each step of a gesture, not to be used directly, use via Gesture class"""

    def __init__(self, pos: tuple, step_type: str, interval: float):
        """
        Initialize a gesture step.

        Args:
            pos (tuple): Tuple containing x and y coordinates.
            step_type (str): Type of step ("start", "move", "pause").
            interval (float): Interval duration in seconds.
        """
        self.pos = pos[0], pos[1]
        self.interval = int(interval * 1000)
        self.type = step_type

    def __repr__(self):
        return f"GestureStep(pos=({self.pos[0]}, {self.pos[1]}), type='{self.type}', interval={self.interval})"

    def __str__(self):
        return self.__repr__()