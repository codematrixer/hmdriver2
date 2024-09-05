# -*- coding: utf-8 -*-

import time
import uuid
from typing import Type, Any, Tuple, Dict, Union, List

try:
    # Python3.8+
    from functools import cached_property
except ImportError:
    from cached_property import cached_property

from .exception import DeviceNotFoundError
from ._client import HMClient
from ._uiobject import UiObject
from .hdc import list_devices
from ._toast import ToastWatcher
from .proto import HypiumResponse, KeyCode, Point, DisplayRotation, DeviceInfo


class Driver:
    _instance: Dict = {}

    def __init__(self, serial: str):
        self.serial = serial
        if not self._is_device_online():
            raise DeviceNotFoundError(f"Device [{self.serial}] not found")

        self._client = HMClient(self.serial)
        self._this_driver = self._client._hdriver.value  # "Driver#0"
        self.hdc = self._client.hdc

    def __new__(cls: Type[Any], serial: str) -> Any:
        """
        Ensure that only one instance of Driver exists per device serial number.
        """
        if serial not in cls._instance:
            cls._instance[serial] = super().__new__(cls)
        return cls._instance[serial]

    def __call__(self, **kwargs) -> UiObject:

        return UiObject(self._client, **kwargs)

    def __del__(self):
        if hasattr(self, '_client') and self._client:
            self._client.release()

    def _is_device_online(self):
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
        """
        Clear the application's cache and data.
        """
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

    def _invoke(self, api: str, args: List = []) -> HypiumResponse:
        return self._client.invoke(api, this=self._this_driver, args=args)

    @cached_property
    def display_size(self) -> Tuple[int, int]:
        api = "Driver.getDisplaySize"
        resp: HypiumResponse = self._invoke(api)
        w, h = resp.result.get("x"), resp.result.get("y")
        return w, h

    @cached_property
    def display_rotation(self) -> DisplayRotation:
        api = "Driver.getDisplayRotation"
        value = self._invoke(api).result
        return DisplayRotation.from_value(value)

    @cached_property
    def device_info(self) -> DeviceInfo:
        """
        Get detailed information about the device.

        Returns:
            DeviceInfo: An object containing various properties of the device.
        """
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

    @cached_property
    def toast_watcher(self):
        return ToastWatcher(self)

    def open_url(self, url: str):
        self.hdc.shell(f"aa start -U {url}")

    def pull_file(self, rpath: str, lpath: str):
        """
        Pull a file from the device to the local machine.

        Args:
            rpath (str): The remote path of the file on the device.
            lpath (str): The local path where the file should be saved.
        """
        self.hdc.recv_file(rpath, lpath)

    def push_file(self, lpath: str, rpath: str):
        """
        Push a file from the local machine to the device.

        Args:
            lpath (str): The local path of the file.
            rpath (str): The remote path where the file should be saved on the device.
        """
        self.hdc.send_file(lpath, rpath)

    def screenshot(self, path: str) -> str:
        """
        Take a screenshot of the device display.

        Args:
            path (str): The local path to save the screenshot.

        Returns:
            str: The path where the screenshot is saved.
        """
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
        Convert percentages to absolute screen coordinates.

        Args:
            x (Union[int, float]): X coordinate as a percentage or absolute value.
            y (Union[int, float]): Y coordinate as a percentage or absolute value.

        Returns:
            Point: A Point object with absolute screen coordinates.
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
        self._invoke(api, args=[point.x, point.y])

    def double_click(self, x: Union[int, float], y: Union[int, float]):
        point = self._to_abs_pos(x, y)
        api = "Driver.doubleClick"
        self._invoke(api, args=[point.x, point.y])

    def long_click(self, x: Union[int, float], y: Union[int, float]):
        point = self._to_abs_pos(x, y)
        api = "Driver.longClick"
        self._invoke(api, args=[point.x, point.y])

    def swipe(self, x1, y1, x2, y2, speed=1000):
        """
        Perform a swipe action on the device screen.

        Args:
            x1 (float): The start X coordinate as a percentage or absolute value.
            y1 (float): The start Y coordinate as a percentage or absolute value.
            x2 (float): The end X coordinate as a percentage or absolute value.
            y2 (float): The end Y coordinate as a percentage or absolute value.
            speed (int, optional): The swipe speed in pixels per second. Default is 1000. Range: 200-40000. If not within the range, set to default value of 600.
        """
        point1 = self._to_abs_pos(x1, y1)
        point2 = self._to_abs_pos(x2, y2)

        self.hdc.swipe(point1.x, point1.y, point2.x, point2.y, speed=speed)

    def input_text(self, x, y, text: str):
        point = self._to_abs_pos(x, y)
        self.hdc.input_text(point.x, point.y, text)

    def dump_hierarchy(self) -> Dict:
        """
        Dump the UI hierarchy of the device screen.

        Returns:
            Dict: The dumped UI hierarchy as a dictionary.
        """
        return self.hdc.dump_hierarchy()
