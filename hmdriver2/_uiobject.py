# -*- coding: utf-8 -*-

import enum
import time
from typing import List, Optional, Any

from . import logger
from ._client import HmClient
from .exception import ElementNotFoundError
from .proto import ComponentData, ByData, HypiumResponse, Point, Bounds, ElementInfo
from .utils import delay


class ByType(enum.Enum):
    """
    UI 元素查找类型枚举
    
    定义了可用于查找 UI 元素的属性类型
    """
    id = "id"                          # 元素 ID
    key = "key"                        # 元素键值
    text = "text"                      # 元素文本
    type = "type"                      # 元素类型
    description = "description"        # 元素描述
    clickable = "clickable"            # 是否可点击
    longClickable = "longClickable"    # 是否可长按
    scrollable = "scrollable"          # 是否可滚动
    enabled = "enabled"                # 是否启用
    focused = "focused"                # 是否获得焦点
    selected = "selected"              # 是否被选中
    checked = "checked"                # 是否被勾选
    checkable = "checkable"            # 是否可勾选
    isBefore = "isBefore"              # 是否在指定元素之前
    isAfter = "isAfter"                # 是否在指定元素之后

    @classmethod
    def verify(cls, value: str) -> bool:
        """
        验证属性类型是否有效
        
        Args:
            value: 要验证的属性类型
            
        Returns:
            bool: 属性类型有效返回 True，否则返回 False
        """
        return any(value == item.value for item in cls)


class UiObject:
    """
    UI 对象类，用于查找和操作 UI 元素
    
    提供了元素查找、属性获取和操作执行的功能
    """
    
    # 默认超时时间（秒）
    DEFAULT_TIMEOUT = 2

    def __init__(self, client: HmClient, **kwargs) -> None:
        """
        初始化 UI 对象
        
        Args:
            client: HmClient 实例
            **kwargs: 查找元素的条件
        """
        self._client = client
        self._raw_kwargs = kwargs

        # 提取特殊参数
        self._index = kwargs.pop("index", 0)
        self._isBefore = kwargs.pop("isBefore", False)
        self._isAfter = kwargs.pop("isAfter", False)

        self._kwargs = kwargs
        self.__verify()

        self._component: Optional[ComponentData] = None  # 缓存找到的组件

    def __str__(self) -> str:
        """返回 UiObject 的字符串表示"""
        return f"UiObject {self._raw_kwargs}"

    def __verify(self) -> None:
        """
        验证查找条件是否有效
        
        Raises:
            ReferenceError: 查找条件无效时抛出
        """
        for k, v in self._kwargs.items():
            if not ByType.verify(k):
                raise ReferenceError(f"{k} 不是有效的查找条件")

    @property
    def count(self) -> int:
        """
        获取匹配条件的元素数量
        
        Returns:
            int: 元素数量
        """
        elements = self.__find_components()
        return len(elements) if elements else 0

    def __len__(self) -> int:
        """支持使用 len() 函数获取元素数量"""
        return self.count

    def exists(self, retries: int = 2, wait_time: float = 1) -> bool:
        """
        检查元素是否存在
        
        Args:
            retries: 重试次数，默认为 2
            wait_time: 重试间隔时间（秒），默认为 1
            
        Returns:
            bool: 元素存在返回 True，否则返回 False
        """
        obj = self.find_component(retries, wait_time)
        return obj is not None

    def __set_component(self, component: ComponentData) -> None:
        """
        设置找到的组件
        
        Args:
            component: 组件数据
        """
        self._component = component

    def find_component(self, retries: int = 1, wait_time: float = 1) -> Optional[ComponentData]:
        """
        查找匹配条件的组件
        
        Args:
            retries: 重试次数，默认为 1
            wait_time: 重试间隔时间（秒），默认为 1
            
        Returns:
            Optional[ComponentData]: 找到的组件，未找到返回 None
        """
        for attempt in range(retries):
            components = self.__find_components()
            if components and self._index < len(components):
                self.__set_component(components[self._index])
                return self._component

            if attempt < retries - 1:
                time.sleep(wait_time)
                logger.info(f"重试查找元素 {self}")

        return None

    def __find_component(self) -> Optional[ComponentData]:
        """
        查找单个匹配条件的组件
        
        该方法直接调用 Driver.findComponent API 查找单个组件
        
        Returns:
            Optional[ComponentData]: 找到的组件，未找到返回 None
        """
        by: ByData = self.__get_by()
        resp: HypiumResponse = self._client.invoke("Driver.findComponent", args=[by.value])
        if not resp.result:
            return None
        return ComponentData(resp.result)

    def __find_components(self) -> Optional[List[ComponentData]]:
        """
        查找所有匹配条件的组件
        
        Returns:
            Optional[List[ComponentData]]: 找到的组件列表，未找到返回 None
        """
        by: ByData = self.__get_by()
        resp: HypiumResponse = self._client.invoke("Driver.findComponents", args=[by.value])
        if not resp.result:
            return None
        components: List[ComponentData] = []
        for item in resp.result:
            components.append(ComponentData(item))

        return components

    def __get_by(self) -> ByData:
        """
        构建查找条件
        
        Returns:
            ByData: 查找条件对象
        """
        this = "On#seed"
        
        # 处理所有查找条件
        for k, v in self._kwargs.items():
            api = f"On.{k}"
            resp: HypiumResponse = self._client.invoke(api, this=this, args=[v])
            this = resp.result

        # 处理位置关系
        if self._isBefore:
            resp: HypiumResponse = self._client.invoke("On.isBefore", this=this, args=[resp.result])

        if self._isAfter:
            resp: HypiumResponse = self._client.invoke("On.isAfter", this=this, args=[resp.result])

        return ByData(resp.result)

    def __operate(self, api: str, args: Optional[List[Any]] = None, retries: int = 2) -> Any:
        """
        对元素执行操作
        
        Args:
            api: 要调用的 API
            args: API 参数，默认为空列表
            retries: 重试次数，默认为 2
            
        Returns:
            Any: API 调用结果
            
        Raises:
            ElementNotFoundError: 元素未找到时抛出
        """
        if args is None:
            args = []
            
        if not self._component:
            if not self.find_component(retries):
                raise ElementNotFoundError(f"未找到元素({self})，重试 {retries} 次后失败")

        resp: HypiumResponse = self._client.invoke(api, this=self._component.value, args=args)
        return resp.result

    @property
    def id(self) -> str:
        """元素 ID"""
        return self.__operate("Component.getId")

    @property
    def key(self) -> str:
        """元素键值"""
        return self.__operate("Component.getId")

    @property
    def type(self) -> str:
        """元素类型"""
        return self.__operate("Component.getType")

    @property
    def text(self) -> str:
        """元素文本"""
        return self.__operate("Component.getText")

    @property
    def description(self) -> str:
        """元素描述"""
        return self.__operate("Component.getDescription")

    @property
    def isSelected(self) -> bool:
        """元素是否被选中"""
        return self.__operate("Component.isSelected")

    @property
    def isChecked(self) -> bool:
        """元素是否被勾选"""
        return self.__operate("Component.isChecked")

    @property
    def isEnabled(self) -> bool:
        """元素是否启用"""
        return self.__operate("Component.isEnabled")

    @property
    def isFocused(self) -> bool:
        """元素是否获得焦点"""
        return self.__operate("Component.isFocused")

    @property
    def isCheckable(self) -> bool:
        """元素是否可勾选"""
        return self.__operate("Component.isCheckable")

    @property
    def isClickable(self) -> bool:
        """元素是否可点击"""
        return self.__operate("Component.isClickable")

    @property
    def isLongClickable(self) -> bool:
        """元素是否可长按"""
        return self.__operate("Component.isLongClickable")

    @property
    def isScrollable(self) -> bool:
        """元素是否可滚动"""
        return self.__operate("Component.isScrollable")

    @property
    def bounds(self) -> Bounds:
        """
        元素边界
        
        Returns:
            Bounds: 元素边界对象
        """
        _raw = self.__operate("Component.getBounds")
        return Bounds(**_raw)

    @property
    def boundsCenter(self) -> Point:
        """
        元素中心点坐标
        
        Returns:
            Point: 元素中心点坐标对象
        """
        _raw = self.__operate("Component.getBoundsCenter")
        return Point(**_raw)

    @property
    def info(self) -> ElementInfo:
        """
        获取元素的完整信息
        
        Returns:
            ElementInfo: 包含元素所有属性的信息对象
        """
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
    def click(self) -> Any:
        """
        点击元素
        
        Returns:
            Any: 操作结果
        """
        return self.__operate("Component.click")

    @delay
    def click_if_exists(self) -> Optional[Any]:
        """
        如果元素存在则点击
        
        与 click() 不同，该方法在元素不存在时不会抛出异常
        
        Returns:
            Optional[Any]: 操作结果，元素不存在时返回 None
        """
        try:
            return self.__operate("Component.click")
        except ElementNotFoundError:
            return None

    @delay
    def double_click(self) -> Any:
        """
        双击元素
        
        Returns:
            Any: 操作结果
        """
        return self.__operate("Component.doubleClick")

    @delay
    def long_click(self) -> Any:
        """
        长按元素
        
        Returns:
            Any: 操作结果
        """
        return self.__operate("Component.longClick")

    @delay
    def drag_to(self, component: ComponentData) -> Any:
        """
        将元素拖动到指定组件位置
        
        Args:
            component: 目标组件
            
        Returns:
            Any: 操作结果
        """
        return self.__operate("Component.dragTo", [component.value])

    @delay
    def input_text(self, text: str) -> Any:
        """
        在元素中输入文本
        
        Args:
            text: 要输入的文本
            
        Returns:
            Any: 操作结果
        """
        return self.__operate("Component.inputText", [text])

    @delay
    def clear_text(self) -> Any:
        """
        清除元素中的文本
        
        Returns:
            Any: 操作结果
        """
        return self.__operate("Component.clearText")

    @delay
    def pinch_in(self, scale: float = 0.5) -> Any:
        """
        在元素上执行捏合手势（缩小）
        
        Args:
            scale: 缩放比例，默认为 0.5
            
        Returns:
            Any: 操作结果
        """
        return self.__operate("Component.pinchIn", [scale])

    @delay
    def pinch_out(self, scale: float = 2) -> Any:
        """
        在元素上执行张开手势（放大）
        
        Args:
            scale: 缩放比例，默认为 2
            
        Returns:
            Any: 操作结果
        """
        return self.__operate("Component.pinchOut", [scale])
