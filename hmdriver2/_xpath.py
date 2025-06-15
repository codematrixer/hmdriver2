# -*- coding: utf-8 -*-

import json
import re
from functools import cached_property
from typing import Dict, Optional, List, Any

from lxml import etree

from . import logger
from .driver import Driver
from .exception import XmlElementNotFoundError
from .proto import Point
from .utils import parse_bounds, delay

# XML相关常量
XML_ROOT_TAG = "orgRoot"
XML_ATTRIBUTE_TYPE = "type"
XML_ATTRIBUTE_BOUNDS = "origBounds"
XML_ATTRIBUTE_ID = "id"
XML_ATTRIBUTE_TEXT = "text"
XML_ATTRIBUTE_DESCRIPTION = "description"

# 布尔属性的默认值
DEFAULT_BOOL_VALUE = "false"
TRUE_VALUE = "true"

# 布尔属性列表
BOOL_ATTRIBUTES = [
    "enabled", "focused", "selected", "checked", "checkable",
    "clickable", "longClickable", "scrollable"
]


class _XPath:
    """
    XPath查询类，用于在UI层次结构中查找元素。
    
    该类提供了将JSON格式的层次结构转换为XML，并执行XPath查询的功能。
    
    Attributes:
        _d (Driver): Driver实例，用于与设备交互
    """

    def __init__(self, d: Driver) -> None:
        """
        初始化XPath查询对象。

        Args:
            d: Driver实例，用于执行设备操作
        """
        self._d = d

    def __call__(self, xpath: str) -> '_XMLElement':
        """
        执行XPath查询并返回匹配的元素。

        Args:
            xpath: XPath查询字符串

        Returns:
            _XMLElement: 匹配XPath查询的XML元素

        Raises:
            RuntimeError: 当层次结构为空或解析失败时抛出
            XmlElementNotFoundError: 当找不到匹配元素时抛出
        """
        hierarchy_str: str = self._d.dump_hierarchy()
        if not hierarchy_str:
            raise RuntimeError("层次结构为空")

        try:
            hierarchy: Dict[str, Any] = json.loads(hierarchy_str)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"解析层次结构JSON失败: {e}")

        xml = self._json2xml(hierarchy)
        
        try:
            result: List[etree.Element] = xml.xpath(xpath)
        except etree.XPathError as e:
            raise RuntimeError(f"XPath查询语法错误: {e}")

        # 返回第一个匹配的节点，如果未找到则返回None
        node = result[0] if result else None
        return _XMLElement(node, self._d)

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """
        移除XML不兼容的控制字符。

        Args:
            text: 需要清理的文本

        Returns:
            str: 清理后的文本
        """
        if not isinstance(text, str):
            text = str(text)
        return re.sub(r'[\x00-\x1F\x7F]', '', text)

    @staticmethod
    def _json2xml(hierarchy: Dict[str, Any]) -> etree.Element:
        """
        将JSON格式的层次结构转换为XML。

        Args:
            hierarchy: JSON格式的层次结构数据

        Returns:
            etree.Element: 转换后的XML元素
        """
        attributes = hierarchy.get("attributes", {})
        cleaned_attributes = {
            k: _XPath._sanitize_text(str(v)) 
            for k, v in attributes.items()
        }
        
        tag = cleaned_attributes.get(XML_ATTRIBUTE_TYPE, XML_ROOT_TAG) or XML_ROOT_TAG
        xml = etree.Element(tag, attrib=cleaned_attributes)
        
        children = hierarchy.get("children", [])
        for item in children:
            xml.append(_XPath._json2xml(item))
            
        return xml


class _XMLElement:
    """
    XML元素类，用于处理UI控件的属性和操作。
    
    提供了控件属性的访问和基本的交互操作方法。
    
    Attributes:
        _node (Optional[etree.Element]): XML节点元素
        _d (Driver): Driver实例
    """

    def __init__(self, node: Optional[etree.Element], d: Driver) -> None:
        """
        初始化XML元素。

        Args:
            node: XML节点元素
            d: Driver实例
        """
        self._node = node
        self._d = d

    def _verify(self) -> None:
        """
        验证控件是否存在。

        Raises:
            XmlElementNotFoundError: 当控件不存在时抛出
        """
        if self._node is None or not self._node.attrib:
            raise XmlElementNotFoundError("未找到匹配的元素")

    @cached_property
    def center(self) -> Point:
        """
        获取控件中心点坐标。

        Returns:
            Point: 控件中心点坐标
            
        Raises:
            XmlElementNotFoundError: 当控件不存在时抛出
        """
        self._verify()
        bounds = parse_bounds(self._node.attrib.get(XML_ATTRIBUTE_BOUNDS, ""))
        return bounds.get_center() if bounds else Point(0, 0)

    def exists(self) -> bool:
        """
        检查控件是否存在。

        Returns:
            bool: 控件存在返回True，否则返回False
        """
        return self._node is not None and bool(self._node.attrib)

    @property
    def id(self) -> str:
        """
        控件的唯一标识符
        
        Returns:
            str: 控件ID
            
        Raises:
            XmlElementNotFoundError: 当控件不存在时抛出
        """
        self._verify()
        return self._node.attrib.get(XML_ATTRIBUTE_ID, "")

    @property
    def type(self) -> str:
        """
        控件的类型
        
        Returns:
            str: 控件类型
            
        Raises:
            XmlElementNotFoundError: 当控件不存在时抛出
        """
        self._verify()
        return self._node.attrib.get(XML_ATTRIBUTE_TYPE, "")

    @property
    def text(self) -> str:
        """
        控件的文本内容
        
        Returns:
            str: 控件文本
            
        Raises:
            XmlElementNotFoundError: 当控件不存在时抛出
        """
        self._verify()
        return self._node.attrib.get(XML_ATTRIBUTE_TEXT, "")

    @property
    def description(self) -> str:
        """
        控件的描述信息
        
        Returns:
            str: 控件描述
            
        Raises:
            XmlElementNotFoundError: 当控件不存在时抛出
        """
        self._verify()
        return self._node.attrib.get(XML_ATTRIBUTE_DESCRIPTION, "")

    def _get_bool_attr(self, attr: str) -> bool:
        """
        获取布尔类型的属性值。

        Args:
            attr: 属性名

        Returns:
            bool: 属性值
            
        Raises:
            XmlElementNotFoundError: 当控件不存在时抛出
        """
        self._verify()
        return self._node.attrib.get(attr, DEFAULT_BOOL_VALUE) == TRUE_VALUE

    @property
    def enabled(self) -> bool:
        """
        控件是否启用
        
        Returns:
            bool: 启用状态
        """
        return self._get_bool_attr("enabled")

    @property
    def focused(self) -> bool:
        """
        控件是否获得焦点
        
        Returns:
            bool: 焦点状态
        """
        return self._get_bool_attr("focused")

    @property
    def selected(self) -> bool:
        """
        控件是否被选中
        
        Returns:
            bool: 选中状态
        """
        return self._get_bool_attr("selected")

    @property
    def checked(self) -> bool:
        """
        控件是否被勾选
        
        Returns:
            bool: 勾选状态
        """
        return self._get_bool_attr("checked")

    @property
    def checkable(self) -> bool:
        """
        控件是否可勾选
        
        Returns:
            bool: 可勾选状态
        """
        return self._get_bool_attr("checkable")

    @property
    def clickable(self) -> bool:
        """
        控件是否可点击
        
        Returns:
            bool: 可点击状态
        """
        return self._get_bool_attr("clickable")

    @property
    def long_clickable(self) -> bool:
        """
        控件是否可长按
        
        Returns:
            bool: 可长按状态
        """
        return self._get_bool_attr("longClickable")

    @property
    def scrollable(self) -> bool:
        """
        控件是否可滚动
        
        Returns:
            bool: 可滚动状态
        """
        return self._get_bool_attr("scrollable")

    @delay
    def click(self) -> None:
        """
        点击控件中心位置。
        
        Raises:
            XmlElementNotFoundError: 当控件不存在时抛出
            
        Note:
            该操作会自动添加延迟以确保操作的稳定性
        """
        self._verify()
        x, y = self.center.x, self.center.y
        logger.debug(f"点击坐标: ({x}, {y})")
        self._d.click(x, y)

    @delay
    def click_if_exists(self) -> bool:
        """
        如果控件存在则点击。
        
        Returns:
            bool: 点击成功返回True，控件不存在返回False
            
        Note:
            该方法不会在控件不存在时抛出异常
        """
        if not self.exists():
            logger.debug("控件不存在，跳过点击操作")
            return False

        x, y = self.center.x, self.center.y
        logger.debug(f"点击坐标: ({x}, {y})")
        self._d.click(x, y)
        return True

    @delay
    def double_click(self) -> None:
        """
        双击控件中心位置。
        
        Raises:
            XmlElementNotFoundError: 当控件不存在时抛出
        """
        self._verify()
        x, y = self.center.x, self.center.y
        logger.debug(f"双击坐标: ({x}, {y})")
        self._d.double_click(x, y)

    @delay
    def long_click(self) -> None:
        """
        长按控件中心位置。
        
        Raises:
            XmlElementNotFoundError: 当控件不存在时抛出
        """
        self._verify()
        x, y = self.center.x, self.center.y
        logger.debug(f"长按坐标: ({x}, {y})")
        self._d.long_click(x, y)

    @delay
    def input_text(self, text: str) -> None:
        """
        在控件中输入文本。

        Args:
            text: 要输入的文本内容
            
        Raises:
            XmlElementNotFoundError: 当控件不存在时抛出
            
        Note:
            会先点击控件获取焦点，然后进行文本输入
        """
        self._verify()
        logger.debug(f"输入文本: {text}")
        self.click()
        self._d.input_text(text)
