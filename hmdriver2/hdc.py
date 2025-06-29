# -*- coding: utf-8 -*-
import tempfile
import json
import uuid
import shlex
import re
import os
import subprocess
from typing import Union, List, Dict, Tuple, Optional

from . import logger
from .utils import FreePort
from .proto import CommandResult, KeyCode
from .exception import HdcError, DeviceNotFoundError


def _execute_command(cmdargs: Union[str, List[str]]) -> CommandResult:
    if isinstance(cmdargs, (list, tuple)):
        cmdline: str = ' '.join(list(map(shlex.quote, cmdargs)))
    elif isinstance(cmdargs, str):
        cmdline = cmdargs

    logger.debug(cmdline)
    try:
        process = subprocess.Popen(cmdline, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=True)
        output, error = process.communicate()
        output = output.decode('utf-8')
        error = error.decode('utf-8')
        exit_code = process.returncode

        if 'error:' in output.lower() or '[fail]' in output.lower():
            return CommandResult("", output, -1)

        return CommandResult(output, error, exit_code)
    except Exception as e:
        return CommandResult("", str(e), -1)


def _build_hdc_prefix() -> str:
    """
    Construct the hdc command prefix based on environment variables.
    """
    host = os.getenv("HDC_SERVER_HOST")
    port = os.getenv("HDC_SERVER_PORT")
    if host and port:
        logger.debug(f"HDC_SERVER_HOST: {host}, HDC_SERVER_PORT: {port}")
        return f"hdc -s {host}:{port}"
    return "hdc"


def list_devices() -> List[str]:
    devices = []
    hdc_prefix = _build_hdc_prefix()
    result = _execute_command(f"{hdc_prefix} list targets")
    if result.exit_code == 0 and result.output:
        lines = result.output.strip().split('\n')
        for line in lines:
            if line.__contains__('Empty'):
                continue
            devices.append(line.strip())

    if result.exit_code != 0:
        raise HdcError("HDC error", result.error)

    return devices


class HdcWrapper:
    def __init__(self, serial: str) -> None:
        self.serial = serial
        self.hdc_prefix = _build_hdc_prefix()

        if not self.is_online():
            raise DeviceNotFoundError(f"Device [{self.serial}] not found")

    def is_online(self):
        _serials = list_devices()
        return True if self.serial in _serials else False

    def forward_port(self, rport: int) -> int:
        lport: int = FreePort().get()
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} fport tcp:{lport} tcp:{rport}")
        if result.exit_code != 0:
            raise HdcError("HDC forward port error", result.error)
        return lport

    def rm_forward(self, lport: int, rport: int) -> int:
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} fport rm tcp:{lport} tcp:{rport}")
        if result.exit_code != 0:
            raise HdcError("HDC rm forward error", result.error)
        return lport

    def list_fport(self) -> List:
        """
        eg.['tcp:10001 tcp:8012', 'tcp:10255 tcp:8012']
        """
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} fport ls")
        if result.exit_code != 0:
            raise HdcError("HDC forward list error", result.error)
        pattern = re.compile(r"tcp:\d+ tcp:\d+")
        return pattern.findall(result.output)

    def send_file(self, lpath: str, rpath: str):
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} file send {lpath} {rpath}")
        if result.exit_code != 0:
            raise HdcError("HDC send file error", result.error)
        return result

    def recv_file(self, rpath: str, lpath: str):
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} file recv {rpath} {lpath}")
        if result.exit_code != 0:
            raise HdcError("HDC receive file error", result.error)
        return result

    def shell(self, cmd: str, error_raise=True) -> CommandResult:
        # ensure the command is wrapped in double quotes
        if cmd[0] != '\"':
            cmd = "\"" + cmd
        if cmd[-1] != '\"':
            cmd += '\"'
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} shell {cmd}")
        if result.exit_code != 0 and error_raise:
            raise HdcError("HDC shell error", f"{cmd}\n{result.output}\n{result.error}")
        return result

    def uninstall(self, bundlename: str):
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} uninstall {bundlename}")
        if result.exit_code != 0:
            raise HdcError("HDC uninstall error", result.output)
        return result

    def install(self, apkpath: str):
        # Ensure the path is properly quoted for Windows
        quoted_path = f'"{apkpath}"'

        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} install {quoted_path}")
        if result.exit_code != 0:
            raise HdcError("HDC install error", result.error)
        return result

    def list_apps(self, include_system_apps: bool = False) -> List[str]:
        """
        List installed applications on the device. (Lazy loading, default: third-party apps)

        Args:
            include_system_apps (bool): If True, include system apps in the list.
                                        If False, only list third-party apps.

        Returns:
            List[str]: A list of application package names.

        Note:
        - When include_system_apps is False, the list typically contains around 50 third-party apps.
        - When include_system_apps is True, the list typically contains around 200 apps in total.
        """
        # Construct the shell command based on the include_system_apps flag
        if include_system_apps:
            command = "bm dump -a"
        else:
            command = "bm dump -a | grep -v 'com.huawei'"

        # Execute the shell command
        result = self.shell(command)
        raw = result.output.split('\n')

        # Filter out strings starting with 'ID:' and empty strings
        return [item.strip() for item in raw if item.strip() and not re.match(r'^ID:', item.strip())]

    def app_version(self, bundlename: str) -> Dict[str, Optional[str]]:
        """
        Get the version information of an app installed on the device.

        Args:
            bundlename (str): The bundle name of the app.

        Returns:
            dict: A dictionary containing the version information:
                  - "versionName": The version name of the app.
                  - "versionCode": The version code of the app.
        """
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} shell bm dump -n {bundlename} | grep '\"versionCode\":\\|versionName\"'")

        matches = re.findall(r'"versionCode":\s*(\d+),\s*"versionName":\s*"([^"]*)"', result.output)
        if not matches:
            return dict(
                version_name='',
                version_code=''
            )

        # Select the last match
        version_code, version_name = matches[-1]
        version_code = int(version_code) if version_code.isdigit() else None
        version_name = version_name if version_name != "" else None

        return dict(
            version_name=version_name,
            version_code=version_code
        )

    def has_app(self, package_name: str) -> bool:
        data = self.shell("bm dump -a").output
        return True if package_name in data else False

    def start_app(self, package_name: str, ability_name: str):
        return self.shell(f"aa start -a {ability_name} -b {package_name}")

    def stop_app(self, package_name: str):
        return self.shell(f"aa force-stop {package_name}")

    def current_app(self) -> Tuple[str, str]:
        """
        Get the current foreground application information.

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

        data: CommandResult = self.shell("aa dump -l")
        output = data.output
        results = __extract_info(output)
        return results[0] if results else (None, None)

    def wakeup(self):
        self.shell("power-shell wakeup")

    def screen_state(self) -> str:
        """
        ["INACTIVE", "SLEEP, AWAKE"]
        """
        data = self.shell("hidumper -s PowerManagerService -a -s").output
        pattern = r"Current State:\s*(\w+)"
        match = re.search(pattern, data)

        return match.group(1) if match else None

    def wlan_ip(self) -> Union[str, None]:
        data = self.shell("ifconfig").output
        matches = re.findall(r'inet addr:(?!127)(\d+\.\d+\.\d+\.\d+)', data)
        return matches[0] if matches else None

    def __split_text(self, text: str) -> str:
        return text.split("\n")[0].strip() if text else None

    def sdk_version(self) -> str:
        data = self.shell("param get const.ohos.apiversion").output
        return self.__split_text(data)

    def sys_version(self) -> str:
        data = self.shell("param get const.product.software.version").output
        return self.__split_text(data)

    def model(self) -> str:
        data = self.shell("param get const.product.model").output
        return self.__split_text(data)

    def brand(self) -> str:
        data = self.shell("param get const.product.brand").output
        return self.__split_text(data)

    def product_name(self) -> str:
        data = self.shell("param get const.product.name").output
        return self.__split_text(data)

    def cpu_abi(self) -> str:
        data = self.shell("param get const.product.cpu.abilist").output
        return self.__split_text(data)

    def display_size(self) -> Tuple[int, int]:
        data = self.shell("hidumper -s RenderService -a screen").output
        match = re.search(r'activeMode:\s*(\d+)x(\d+),\s*refreshrate=\d+', data)

        if match:
            w = int(match.group(1))
            h = int(match.group(2))
            return (w, h)
        return (0, 0)

    def send_key(self, key_code: Union[KeyCode, int]) -> None:
        if isinstance(key_code, KeyCode):
            key_code = key_code.value

        MAX = 3200
        if key_code > MAX:
            raise HdcError("Invalid HDC keycode")

        self.shell(f"uitest uiInput keyEvent {key_code}")

    def tap(self, x: int, y: int) -> None:
        self.shell(f"uitest uiInput click {x} {y}")

    def swipe(self, x1, y1, x2, y2, speed=1000):
        self.shell(f"uitest uiInput swipe {x1} {y1} {x2} {y2} {speed}")

    def input_text(self, x: int, y: int, text: str):
        self.shell(f"uitest uiInput inputText {x} {y} {text}")

    def screenshot(self, path: str, method: str = "snapshot_display") -> str:
        """
        Take a screenshot using one of the two available methods.

        Args:
            path (str): The local path where the screenshot will be saved.
            method (str): The screenshot method to use. Options are:
                          - "snapshot_display" (default, recommended for better performance)
                            This method is faster and more efficient, but the image quality is lower.
                          - "screenCap" (alternative method)
                            This method produces higher-quality images (5~20 times clearer), but it is slower.

        Returns:
            str: The local path where the screenshot is saved.
        """
        if method == "snapshot_display":
            # Use the recommended method (snapshot_display)
            _uuid = uuid.uuid4().hex
            _tmp_path = f"/data/local/tmp/_tmp_{_uuid}.jpeg"
            self.shell(f"snapshot_display -f {_tmp_path}")
            self.recv_file(_tmp_path, path)
            self.shell(f"rm -rf {_tmp_path}")
        elif method == "screenCap":
            # Use the alternative method (screenCap)
            _uuid = uuid.uuid4().hex
            _tmp_path = f"/data/local/tmp/{_uuid}.png"
            self.shell(f"uitest screenCap -p {_tmp_path}")
            self.recv_file(_tmp_path, path)
            self.shell(f"rm -rf {_tmp_path}")
        else:
            raise ValueError(f"Invalid screenshot method: {method}. Use 'snapshot_display' or 'screenCap'.")

        return path

    def dump_hierarchy(self) -> Dict:
        _tmp_path = f"/data/local/tmp/{self.serial}_tmp.json"
        self.shell(f"uitest dumpLayout -p {_tmp_path}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            path = f.name
            self.recv_file(_tmp_path, path)

            try:
                with open(path, 'r', encoding='utf8') as file:
                    data = json.load(file)
            except Exception as e:
                logger.error(f"Error loading JSON file: {e}")
                data = {}

            return data
