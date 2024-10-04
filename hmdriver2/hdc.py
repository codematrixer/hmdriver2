# -*- coding: utf-8 -*-

import tempfile
import json
import uuid
import shlex
import re
import subprocess
from typing import Union, List, Dict

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

        if output.lower().__contains__('error:'):
            return CommandResult("", output, -1)

        return CommandResult(output, error, exit_code)
    except Exception as e:
        return CommandResult("", str(e), -1)


def list_devices() -> List[str]:
    devices = []
    result = _execute_command('hdc list targets')
    if result.exit_code == 0 and result.output:
        lines = result.output.strip().split('\n')
        for line in lines:
            if line.__contains__('Empty'):
                continue
            devices.append(line.strip())
    return devices


class HdcWrapper:
    def __init__(self, serial: str) -> None:
        self.serial = serial
        if not self.is_online():
            raise DeviceNotFoundError(f"Device [{self.serial}] not found")

    def is_online(self):
        _serials = list_devices()
        return True if self.serial in _serials else False

    def forward_port(self, rport: int) -> int:
        lport: int = FreePort().get()
        result = _execute_command(f"hdc -t {self.serial} fport tcp:{lport} tcp:{rport}")
        if result.exit_code != 0:
            raise HdcError("HDC forward port error", result.error)
        return lport

    def rm_forward(self, lport: int, rport: int) -> int:
        result = _execute_command(f"hdc -t {self.serial} fport rm tcp:{lport} tcp:{rport}")
        if result.exit_code != 0:
            raise HdcError("HDC rm forward error", result.error)
        return lport

    def list_fport(self) -> List:
        """
        eg.['tcp:10001 tcp:8012', 'tcp:10255 tcp:8012']
        """
        result = _execute_command(f"hdc -t {self.serial} fport ls")
        if result.exit_code != 0:
            raise HdcError("HDC forward list error", result.error)
        pattern = re.compile(r"tcp:\d+ tcp:\d+")
        return pattern.findall(result.output)

    def send_file(self, lpath: str, rpath: str):
        result = _execute_command(f"hdc -t {self.serial} file send {lpath} {rpath}")
        if result.exit_code != 0:
            raise HdcError("HDC send file error", result.error)
        return result

    def recv_file(self, rpath: str, lpath: str):
        result = _execute_command(f"hdc -t {self.serial} file recv {rpath} {lpath}")
        if result.exit_code != 0:
            raise HdcError("HDC receive file error", result.error)
        return result

    def shell(self, cmd: str, error_raise=True) -> CommandResult:
        result = _execute_command(f"hdc -t {self.serial} shell {cmd}")
        if result.exit_code != 0 and error_raise:
            raise HdcError("HDC shell error", f"{cmd}\n{result.output}\n{result.error}")
        return result

    def uninstall(self, bundlename: str):
        result = _execute_command(f"hdc -t {self.serial} uninstall {bundlename}")
        if result.exit_code != 0:
            raise HdcError("HDC uninstall error", result.output)
        return result

    def install(self, apkpath: str):
        result = _execute_command(f"hdc -t {self.serial} install '{apkpath}'")
        if result.exit_code != 0:
            raise HdcError("HDC install error", result.error)
        return result

    def list_apps(self) -> List[str]:
        result = self.shell("bm dump -a")
        raw = result.output.split('\n')
        return [item.strip() for item in raw]

    def has_app(self, package_name: str) -> bool:
        data = self.shell("bm dump -a").output
        return True if package_name in data else False

    def start_app(self, package_name: str, ability_name: str):
        return self.shell(f"aa start -a {ability_name} -b {package_name}")

    def stop_app(self, package_name: str):
        return self.shell(f"aa force-stop {package_name}")

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

    def screenshot(self, path: str) -> str:
        _uuid = uuid.uuid4().hex
        _tmp_path = f"/data/local/tmp/_tmp_{_uuid}.jpeg"
        self.shell(f"snapshot_display -f {_tmp_path}")
        self.recv_file(_tmp_path, path)
        self.shell(f"rm -rf {_tmp_path}")  # remove local path
        return path

    def dump_hierarchy(self) -> Dict:
        _tmp_path = "/data/local/tmp/_tmp.json"
        self.shell(f"uitest dumpLayout -p {_tmp_path}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            path = f.name
            self.recv_file(_tmp_path, path)

            try:
                with open(path, 'r') as file:
                    data = json.load(file)
            except Exception as e:
                logger.error(f"Error loading JSON file: {e}")
                data = {}

            return data
