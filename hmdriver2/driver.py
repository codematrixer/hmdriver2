# -*- coding: utf-8 -*-

import json
import uuid
import re
from typing import Type, Any, Tuple, Dict, Union, List
from functools import cached_property  # python3.8+

from . import logger
from .utils import delay
from ._client import HmClient
from ._uiobject import UiObject
from .proto import HypiumResponse, KeyCode, Point, DisplayRotation, DeviceInfo, CommandResult


class Driver:
    _instance: Dict = {}

    def __init__(self, serial: str):
        self.serial = serial
        self._client = HmClient(self.serial)
        self.hdc = self._client.hdc

        self._init_hmclient()

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

    def _init_hmclient(self):
        self._client.start()

    def _invoke(self, api: str, args: List = []) -> HypiumResponse:
        return self._client.invoke(api, this="Driver#0", args=args)

    @delay
    def start_app(self, package_name: str, page_name: str = "MainAbility"):
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

    def current_app(self) -> Tuple[str, str]:
        """
        Get the current foreground application information.

        This method executes a shell command to dump the current application state and extracts
        the package_name and page_name of the application that is in the foreground state.

        Returns:
            Tuple[str, str]: A tuple contain the package_name andpage_name of the foreground application.
                             If no foreground application is found, returns (None, None).
        """

        def __extract_info(output: str):
            results = []

            mission_blocks = re.findall(r'Mission ID #[\s\S]*?isKeepAlive: false\s*}', output)
            if not mission_blocks:
                return results

            for block in mission_blocks:
                if 'state #FOREGROUND' in block:
                    bundle_name_match = re.search(r'bundle name \[(.*?)\]', block)
                    main_name_match = re.search(r'main name \[(.*?)\]', block)
                    if bundle_name_match and main_name_match:
                        package_name = bundle_name_match.group(1)
                        page_name = main_name_match.group(1)
                        results.append((package_name, page_name))

            return results

        data: CommandResult = self.hdc.shell("aa dump -l")
        output = data.output
        results = __extract_info(output)
        return results[0] if results else (None, None)

    def get_app_info(self, package_name: str) -> Dict:
        """
        Get detailed information about a specific application.

        This method executes a shell command to dump the application information for the given package name
        and parses the output as JSON to extract the application details.

        Args:
            package_name (str): The package name of the application to retrieve information for.

        Returns:
            Dict: A dictionary containing the application information. If an error occurs during parsing,
                  an empty dictionary is returned.
        """
        app_info = {}
        data: CommandResult = self.hdc.shell(f"bm dump -n {package_name}")
        output = data.output
        try:
            json_start = output.find("{")
            json_end = output.rfind("}") + 1
            json_output = output[json_start:json_end]

            app_info = json.loads(json_output)
        except Exception as e:
            logger.error(f"An error occurred:{e}")
        return app_info

    @cached_property
    def toast_watcher(self):

        obj = self

        class _Watcher:
            def start(self) -> bool:
                api = "Driver.uiEventObserverOnce"
                resp: HypiumResponse = obj._invoke(api, args=["toastShow"])
                return resp.result

            def get_toast(self, timeout: int = 3) -> str:
                api = "Driver.getRecentUiEvent"
                resp: HypiumResponse = obj._invoke(api, args=[timeout])
                if resp.result:
                    return resp.result.get("text")
                return None

        return _Watcher()

    @delay
    def go_back(self):
        self.hdc.send_key(KeyCode.BACK)

    @delay
    def go_home(self):
        self.hdc.send_key(KeyCode.HOME)

    @delay
    def press_key(self, key_code: Union[KeyCode, int]):
        self.hdc.send_key(key_code)

    def screen_on(self):
        self.hdc.wakeup()

    def screen_off(self):
        self.hdc.wakeup()
        self.press_key(KeyCode.POWER)

    @delay
    def unlock(self):
        self.screen_on()
        w, h = self.display_size
        self.swipe(0.5 * w, 0.8 * h, 0.5 * w, 0.2 * h, speed=6000)

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

    def set_display_rotation(self, rotation: DisplayRotation):
        """
        Sets the display rotation to the specified orientation.

        Args:
            rotation (DisplayRotation): The desired display rotation. This should be an instance of the DisplayRotation enum.
        """
        api = "Driver.setDisplayRotation"
        self._invoke(api, args=[rotation.value])

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

    @delay
    def open_url(self, url: str, system_browser: bool = True):
        if system_browser:
            # Use the system browser
            self.hdc.shell(f"aa start -A ohos.want.action.viewData -e entity.system.browsable -U {url}")
        else:
            # Default method
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

    def shell(self, cmd) -> CommandResult:
        return self.hdc.shell(cmd)

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
        return Point(int(x), int(y))

    @delay
    def click(self, x: Union[int, float], y: Union[int, float]):

        # self.hdc.tap(point.x, point.y)
        point = self._to_abs_pos(x, y)
        api = "Driver.click"
        self._invoke(api, args=[point.x, point.y])

    @delay
    def double_click(self, x: Union[int, float], y: Union[int, float]):
        point = self._to_abs_pos(x, y)
        api = "Driver.doubleClick"
        self._invoke(api, args=[point.x, point.y])

    @delay
    def long_click(self, x: Union[int, float], y: Union[int, float]):
        point = self._to_abs_pos(x, y)
        api = "Driver.longClick"
        self._invoke(api, args=[point.x, point.y])

    @delay
    def swipe(self, x1, y1, x2, y2, speed=2000):
        """
        Perform a swipe action on the device screen.

        Args:
            x1 (float): The start X coordinate as a percentage or absolute value.
            y1 (float): The start Y coordinate as a percentage or absolute value.
            x2 (float): The end X coordinate as a percentage or absolute value.
            y2 (float): The end Y coordinate as a percentage or absolute value.
            speed (int, optional): The swipe speed in pixels per second. Default is 2000. Range: 200-40000. If not within the range, set to default value of 2000.
        """

        point1 = self._to_abs_pos(x1, y1)
        point2 = self._to_abs_pos(x2, y2)

        if speed < 200 or speed > 40000:
            logger.warning("`speed` is not in the range[200-40000], Set to default value of 2000.")
            speed = 2000

        api = "Driver.swipe"
        self._invoke(api, args=[point1.x, point1.y, point2.x, point2.y, speed])

    @delay
    def input_text(self, text: str):
        """
        Inputs text into the currently focused input field.

        Note: The input field must have focus before calling this method.

        Args:
            text (str): input value
        """
        return self._invoke("Driver.inputText", args=[{"x": 1, "y": 1}, text])

    def dump_hierarchy(self) -> Dict:
        """
        Dump the UI hierarchy of the device screen.

        Returns:
            Dict: The dumped UI hierarchy as a dictionary.
        """
        # return self._client.invoke_captures("captureLayout").result
        return self.hdc.dump_hierarchy()

    @cached_property
    def gesture(self):
        from ._gesture import _Gesture
        return _Gesture(self)

    @cached_property
    def screenrecord(self):
        from ._screenrecord import RecordClient
        return RecordClient(self.serial, self)

    def _invalidate_cache(self, attribute_name):
        """
        Invalidate the cached property.

        Args:
            attribute_name (str): The name of the attribute to invalidate.
        """
        if attribute_name in self.__dict__:
            del self.__dict__[attribute_name]
