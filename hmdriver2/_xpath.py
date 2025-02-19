# -*- coding: utf-8 -*-

from typing import Dict
from lxml import etree
from functools import cached_property

from . import logger
from .proto import Bounds
from .driver import Driver
from .utils import delay, parse_bounds
from .exception import XmlElementNotFoundError


class _XPath:
    def __init__(self, d: Driver,first_event=True):
        self._d = d
        self.first_event=first_event

    def __call__(self, xpath: str) -> '_XMLElement':

        hierarchy: Dict = self._d.dump_hierarchy()
        if not hierarchy:
            raise RuntimeError("hierarchy is empty")

        xml = _XPath._json2xml(hierarchy)
        result = xml.xpath(xpath)

        if len(result) > 0:
            if self.first_event:
                node = result[0]
                raw_bounds: str = node.attrib.get("bounds")  # [832,1282][1125,1412]
                bounds: Bounds = parse_bounds(raw_bounds)
                logger.debug(f"{xpath} Bounds: {bounds}")
                return _XMLElement(bounds, self._d)
            else:
                result_event_list = []
                for node in result:
                    raw_bounds: str = node.attrib.get("bounds")  # [832,1282][1125,1412]
                    bounds: Bounds = parse_bounds(raw_bounds)
                    logger.debug(f"{xpath} Bounds: {bounds}")
                    result_event_list.append(_XMLElement2(bounds, self._d))
                return result_event_list


        return _XMLElement(None, self._d)

    @staticmethod
    def _json2xml(hierarchy: Dict) -> etree.Element:
        attributes = hierarchy.get("attributes", {})
        tag = attributes.get("type", "orgRoot") or "orgRoot"
        xml = etree.Element(tag, attrib=attributes)

        children = hierarchy.get("children", [])
        for item in children:
            xml.append(_XPath._json2xml(item))
        return xml


class _XMLElement:
    def __init__(self, bounds: Bounds, d: Driver):
        self.bounds = bounds
        self._d = d

    def _verify(self):
        if not self.bounds:
            raise XmlElementNotFoundError("xpath not found")

    @cached_property
    def center(self):
        self._verify()
        return self.bounds.get_center()

    def exists(self) -> bool:
        return self.bounds is not None

    @delay
    def click(self):
        x, y = self.center.x, self.center.y
        self._d.click(x, y)

    @delay
    def click_if_exists(self):

        if not self.exists():
            logger.debug("click_exist: xpath not found")
            return

        x, y = self.center.x, self.center.y
        self._d.click(x, y)

    @delay
    def double_click(self):
        x, y = self.center.x, self.center.y
        self._d.double_click(x, y)

    @delay
    def long_click(self):
        x, y = self.center.x, self.center.y
        self._d.long_click(x, y)

    @delay
    def input_text(self, text):
        self.click()
        self._d.input_text(text)