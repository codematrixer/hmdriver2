# -*- coding: utf-8 -*-

import enum
import time
from typing import List, Union

from . import logger
from .utils import delay
from ._client import HmClient
from .exception import ElementNotFoundError
from .proto import ComponentData, ByData, HypiumResponse, Point, Rect, ElementInfo


class ByType(enum.Enum):
    id = "id"
    key = "key"
    text = "text"
    type = "type"
    description = "description"
    clickable = "clickable"
    longClickable = "longClickable"
    scrollable = "scrollable"
    enabled = "enabled"
    focused = "focused"
    selected = "selected"
    checked = "checked"
    checkable = "checkable"
    isBefore = "isBefore"
    isAfter = "isAfter"

    @classmethod
    def verify(cls, value):
        return any(value == item.value for item in cls)


class UiObject:
    DEFAULT_TIMEOUT = 2

    def __init__(self, client: HmClient, **kwargs) -> None:
        self._client = client
        self._raw_kwargs = kwargs

        self._index = kwargs.pop("index", 0)
        self._isBefore = kwargs.pop("isBefore", False)
        self._isAfter = kwargs.pop("isAfter", False)

        self._kwargs = kwargs
        self.__verify()

        self._component: Union[ComponentData, None] = None  # cache

    def __str__(self) -> str:
        return f"UiObject [{self._raw_kwargs}"

    def __verify(self):
        for k, v in self._kwargs.items():
            if not ByType.verify(k):
                raise ReferenceError(f"{k} is not allowed.")

    @property
    def count(self) -> int:
        eleements = self.__find_components()
        return len(eleements) if eleements else 0

    def __len__(self):
        return self.count

    def exists(self, retries: int = 2, wait_time=1) -> bool:
        obj = self.find_component(retries, wait_time)
        return True if obj else False

    def __set_component(self, component: ComponentData):
        self._component = component

    def find_component(self, retries: int = 1, wait_time=1) -> ComponentData:
        for attempt in range(retries):
            components = self.__find_components()
            if components and self._index < len(components):
                self.__set_component(components[self._index])
                return self._component

            if attempt < retries:
                time.sleep(wait_time)
                logger.info(f"Retry found element {self}")

        return None

    # useless
    def __find_component(self) -> Union[ComponentData, None]:
        by: ByData = self.__get_by()
        resp: HypiumResponse = self._client.invoke("Driver.findComponent", args=[by.value])
        if not resp.result:
            return None
        return ComponentData(resp.result)

    def __find_components(self) -> Union[List[ComponentData], None]:
        by: ByData = self.__get_by()
        resp: HypiumResponse = self._client.invoke("Driver.findComponents", args=[by.value])
        if not resp.result:
            return None
        components: List[ComponentData] = []
        for item in resp.result:
            components.append(ComponentData(item))

        return components

    def __get_by(self) -> ByData:
        for k, v in self._kwargs.items():
            api = f"On.{k}"
            this = "On#seed"
            resp: HypiumResponse = self._client.invoke(api, this, args=[v])
            this = resp.result

        if self._isBefore:
            resp: HypiumResponse = self._client.invoke("On.isBefore", this="On#seed", args=[resp.result])

        if self._isAfter:
            resp: HypiumResponse = self._client.invoke("On.isAfter", this="On#seed", args=[resp.result])

        return ByData(resp.result)

    def __operate(self, api, args=[], retries: int = 2):
        if not self._component:
            if not self.find_component(retries):
                raise ElementNotFoundError(f"Element({self}) not found after {retries} retries")

        resp: HypiumResponse = self._client.invoke(api, this=self._component.value, args=args)
        return resp.result

    @property
    def id(self) -> str:
        return self.__operate("Component.getId")

    @property
    def key(self) -> str:
        return self.__operate("Component.getId")

    @property
    def type(self) -> str:
        return self.__operate("Component.getType")

    @property
    def text(self) -> str:
        return self.__operate("Component.getText")

    @property
    def description(self) -> str:
        return self.__operate("Component.getDescription")

    @property
    def isSelected(self) -> bool:
        return self.__operate("Component.isSelected")

    @property
    def isChecked(self) -> bool:
        return self.__operate("Component.isChecked")

    @property
    def isEnabled(self) -> bool:
        return self.__operate("Component.isEnabled")

    @property
    def isFocused(self) -> bool:
        return self.__operate("Component.isFocused")

    @property
    def isCheckable(self) -> bool:
        return self.__operate("Component.isCheckable")

    @property
    def isClickable(self) -> bool:
        return self.__operate("Component.isClickable")

    @property
    def isLongClickable(self) -> bool:
        return self.__operate("Component.isLongClickable")

    @property
    def isScrollable(self) -> bool:
        return self.__operate("Component.isScrollable")

    @property
    def bounds(self) -> Rect:
        _raw = self.__operate("Component.getBounds")
        return Rect(**_raw)

    @property
    def boundsCenter(self) -> Point:
        _raw = self.__operate("Component.getBoundsCenter")
        return Point(**_raw)

    @property
    def info(self) -> ElementInfo:
        return ElementInfo(
            id=self.id,
            key=self.key,
            type=self.type,
            text=self.text,
            description=self.description,
            isSelected=self.isSelected,
            isChecked=self.isChecked,
            isEnabled=self.isEnabled,
            isFocused=self.isFocused,
            isCheckable=self.isCheckable,
            isClickable=self.isClickable,
            isLongClickable=self.isLongClickable,
            isScrollable=self.isScrollable,
            bounds=self.bounds,
            boundsCenter=self.boundsCenter)

    @delay
    def click(self):
        return self.__operate("Component.click")

    @delay
    def click_if_exists(self):
        try:
            return self.__operate("Component.click")
        except ElementNotFoundError:
            pass

    @delay
    def double_click(self):
        return self.__operate("Component.doubleClick")

    @delay
    def long_click(self):
        return self.__operate("Component.longClick")

    @delay
    def drag_to(self, component: ComponentData):
        return self.__operate("Component.dragTo", [component.value])

    @delay
    def input_text(self, text: str):
        return self.__operate("Component.inputText", [text])

    @delay
    def clear_text(self):
        return self.__operate("Component.clearText")

    @delay
    def pinch_in(self, scale: float = 0.5):
        return self.__operate("Component.pinchIn", [scale])

    @delay
    def pinch_out(self, scale: float = 2):
        return self.__operate("Component.pinchOut", [scale])
