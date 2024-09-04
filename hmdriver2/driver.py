# -*- coding: utf-8 -*-

import atexit
import time
import uuid
from typing import Type, Any, Tuple, Dict, Union, List

try:
    # Python3.8+
    from functools import cached_property
except ImportError:
    from cached_property import cached_property

from . import logger
from .exception import DeviceNotFoundError
from ._client import HMClient
from ._uiobject import UiObject
from .hdc import list_devices
from .proto import HypiumResponse, KeyCode, Point, DisplayRotation, DeviceInfo


class Driver:
    _instance: Dict = {}

    def __init__(self, serial: str):
        self.serial = serial
        if not self._check_serial():
            raise DeviceNotFoundError(f"Device [{self.serial}] not found")

        self._client = HMClient(self.serial)
        self._this_driver = self._client._hdriver.value  # "Driver#0"
        self.hdc = self._client.hdc

    def __new__(cls: Type[Any], serial: str) -> Any:
        if serial not in cls._instance:
            cls._instance[serial] = super().__new__(cls)
        return cls._instance[serial]

    def __call__(self, **kwargs) -> UiObject:
        return UiObject(self._client, **kwargs)

    def __del__(self):
        self._client.release()

    def _check_serial(self):
        _serials = list_devices()
        return True if self.serial in _serials else False

    def start_app(self, package_name: str, page_name: str = "MainAbility"):
        self.unlock()
        self.hdc.start_app(package_name, page_name)

    def force_start_app(self, package_name: str, page_name: str = "MainAbility"):
        self.go_home()
        self.stop_app(package_name)
        self.start_app(package_name, page_name)

    def stop_app(self, package_name: str):
        self.hdc.stop_app(package_name)

    def clear_app(self, package_name: str):
        self.hdc.shell(f"bm clean -n {package_name} -c")  # clear cache
        self.hdc.shell(f"bm clean -n {package_name} -d")  # clear data

    def install_app(self, apk_path: str):
        self.hdc.install(apk_path)

    def uninstall_app(self, package_name: str):
        self.hdc.uninstall(package_name)

    def list_apps(self) -> List:
        return self.hdc.list_apps()

    def has_app(self, package_name: str) -> bool:
        return self.hdc.has_app(package_name)

    def go_back(self):
        self.hdc.send_key(KeyCode.BACK)

    def go_home(self):
        self.hdc.send_key(KeyCode.HOME)

    def press_key(self, key_code: Union[KeyCode, int]):
        self.hdc.send_key(key_code)

    def screen_on(self):
        self.hdc.wakeup()

    def screen_off(self):
        self.hdc.wakeup()
        self.press_key(KeyCode.POWER)

    def unlock(self):
        self.screen_on()
        w, h = self.display_size
        self.hdc.swipe(0.5 * w, 0.8 * h, 0.5 * w, 0.2 * h)
        time.sleep(.5)

    @cached_property
    def display_size(self) -> Tuple[int, int]:
        api = "Driver.getDisplaySize"
        resp: HypiumResponse = self._client.invoke(api, self._this_driver)
        w, h = resp.result.get("x"), resp.result.get("y")
        return w, h

    @cached_property
    def display_rotation(self) -> DisplayRotation:
        api = "Driver.getDisplayRotation"
        value = self._client.invoke(api, self._this_driver).result
        return DisplayRotation.from_value(value)

    @cached_property
    def device_info(self) -> DeviceInfo:
        hdc = self.hdc
        return DeviceInfo(
            productName=hdc.product_name(),
            model=hdc.model(),
            sdkVersion=hdc.sdk_version(),
            sysVersion=hdc.sys_version(),
            cpuAbi=hdc.cpu_abi(),
            wlanIp=hdc.wlan_ip(),
            displaySize=self.display_size,
            displayRotation=self.display_rotation
        )

    def open_url(self, url: str):
        self.hdc.shell(f"aa start -U {url}")

    def pull_file(self, rpath: str, lpath: str):
        self.hdc.recv_file(rpath, lpath)

    def push_file(self, lpath: str, rpath: str):
        self.hdc.send_file(lpath, rpath)

    def screenshot(self, path: str) -> str:
        _uuid = uuid.uuid4().hex
        _tmp_path = f"/data/local/tmp/_tmp_{_uuid}.jpeg"
        self.shell(f"snapshot_display -f {_tmp_path}")
        self.pull_file(_tmp_path, path)
        self.shell(f"rm -rf {_tmp_path}")  # remove local path
        return path

    def shell(self, cmd):
        self.hdc.shell(cmd)

    def _to_abs_pos(self, x: Union[int, float], y: Union[int, float]) -> Point:
        """
        returns a function which can convert percent size to abs size
        """
        assert x >= 0
        assert y >= 0

        w, h = self.display_size

        if x < 1:
            x = int(w * x)
        if y < 1:
            y = int(h * y)
        return Point(x, y)

    def click(self, x: Union[int, float], y: Union[int, float]):

        # self.hdc.tap(point.x, point.y)
        point = self._to_abs_pos(x, y)
        api = "Driver.click"
        self._client.invoke(api, self._this_driver, args=[point.x, point.y])

    def double_click(self, x: Union[int, float], y: Union[int, float]):
        point = self._to_abs_pos(x, y)
        api = "Driver.doubleClick"
        self._client.invoke(api, self._this_driver, args=[point.x, point.y])

    def long_click(self, x: Union[int, float], y: Union[int, float]):
        point = self._to_abs_pos(x, y)
        api = "Driver.longClick"
        self._client.invoke(api, self._this_driver, args=[point.x, point.y])

    def swipe(self, x1, y1, x2, y2, speed=1000):
        """
        speed为滑动速率, 范围:200-40000, 不在范围内设为默认值为600, 单位: 像素点/秒
        """
        point1 = self._to_abs_pos(x1, y1)
        point2 = self._to_abs_pos(x2, y2)

        self.hdc.swipe(point1.x, point1.y, point2.x, point2.y, speed=speed)

    def input_text(self, x, y, text: str):
        point = self._to_abs_pos(x, y)
        self.hdc.input_text(point.x, point.y, text)
