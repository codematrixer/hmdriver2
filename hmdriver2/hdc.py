# -*- coding: utf-8 -*-

import json
import os
import re
import shlex
import subprocess
import tempfile
import uuid
from typing import Union, List, Dict, Tuple, Optional, Any

from . import logger
from .exception import HdcError, DeviceNotFoundError
from .proto import CommandResult, KeyCode
from .utils import FreePort

# HDC 命令相关常量
HDC_CMD = "hdc"
HDC_SERVER_HOST_ENV = "HDC_SERVER_HOST"
HDC_SERVER_PORT_ENV = "HDC_SERVER_PORT"

# 键码相关常量
MAX_KEY_CODE = 3200


def _execute_command(cmdargs: Union[str, List[str]]) -> CommandResult:
    """
    执行命令并返回结果
    
    Args:
        cmdargs: 要执行的命令，可以是字符串或命令参数列表
        
    Returns:
        CommandResult: 命令执行结果对象
    """
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

        # 检查输出中是否包含错误信息
        if 'error:' in output.lower() or '[fail]' in output.lower():
            return CommandResult("", output, -1)

        return CommandResult(output, error, exit_code)
    except Exception as e:
        return CommandResult("", str(e), -1)


def _build_hdc_prefix() -> str:
    """
    根据环境变量构建 HDC 命令前缀
    
    如果设置了 HDC_SERVER_HOST 和 HDC_SERVER_PORT 环境变量，
    则使用这些值构建带有服务器连接信息的命令前缀。
    
    Returns:
        str: HDC 命令前缀
    """
    host = os.getenv(HDC_SERVER_HOST_ENV)
    port = os.getenv(HDC_SERVER_PORT_ENV)
    if host and port:
        logger.debug(f"{HDC_SERVER_HOST_ENV}: {host}, {HDC_SERVER_PORT_ENV}: {port}")
        return f"{HDC_CMD} -s {host}:{port}"
    return HDC_CMD


def list_devices() -> List[str]:
    """
    列出所有已连接的设备
    
    Returns:
        List[str]: 设备序列号列表
        
    Raises:
        HdcError: HDC 命令执行失败时抛出
    """
    devices = []
    hdc_prefix = _build_hdc_prefix()
    result = _execute_command(f"{hdc_prefix} list targets")
    
    if result.exit_code == 0 and result.output:
        lines = result.output.strip().split('\n')
        for line in lines:
            if 'Empty' in line:
                continue
            devices.append(line.strip())

    if result.exit_code != 0:
        raise HdcError("HDC 错误", result.error)

    return devices


class HdcWrapper:
    """
    HDC 命令包装类
    
    提供对 HDC 命令的封装，简化与 Harmony OS 设备的交互。
    """
    
    def __init__(self, serial: str) -> None:
        """
        初始化 HDC 包装器
        
        Args:
            serial: 设备序列号
            
        Raises:
            DeviceNotFoundError: 设备未找到时抛出
        """
        self.serial = serial
        self.hdc_prefix = _build_hdc_prefix()

        if not self.is_online():
            raise DeviceNotFoundError(f"未找到设备 [{self.serial}]")

    def is_online(self) -> bool:
        """
        检查设备是否在线
        
        Returns:
            bool: 设备在线返回 True，否则返回 False
        """
        _serials = list_devices()
        return self.serial in _serials

    def forward_port(self, rport: int) -> int:
        """
        设置端口转发
        
        将设备上的端口转发到本地端口
        
        Args:
            rport: 设备端口
            
        Returns:
            int: 本地端口
            
        Raises:
            HdcError: 端口转发失败时抛出
        """
        lport: int = FreePort().get()
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} fport tcp:{lport} tcp:{rport}")
        if result.exit_code != 0:
            raise HdcError("HDC 端口转发错误", result.error)
        return lport

    def rm_forward(self, lport: int, rport: int) -> int:
        """
        移除端口转发
        
        Args:
            lport: 本地端口
            rport: 设备端口
            
        Returns:
            int: 本地端口
            
        Raises:
            HdcError: 移除端口转发失败时抛出
        """
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} fport rm tcp:{lport} tcp:{rport}")
        if result.exit_code != 0:
            raise HdcError("HDC 移除端口转发错误", result.error)
        return lport

    def list_fport(self) -> List[str]:
        """
        列出所有端口转发
        
        Returns:
            List[str]: 端口转发列表，例如 ['tcp:10001 tcp:8012', 'tcp:10255 tcp:8012']
            
        Raises:
            HdcError: 列出端口转发失败时抛出
        """
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} fport ls")
        if result.exit_code != 0:
            raise HdcError("HDC 列出端口转发错误", result.error)
        pattern = re.compile(r"tcp:\d+ tcp:\d+")
        return pattern.findall(result.output)

    def send_file(self, lpath: str, rpath: str) -> CommandResult:
        """
        发送文件到设备
        
        Args:
            lpath: 本地文件路径
            rpath: 设备上的目标路径
            
        Returns:
            CommandResult: 命令执行结果
            
        Raises:
            HdcError: 发送文件失败时抛出
        """
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} file send {lpath} {rpath}")
        if result.exit_code != 0:
            raise HdcError("HDC 发送文件错误", result.error)
        return result

    def recv_file(self, rpath: str, lpath: str) -> CommandResult:
        """
        从设备接收文件
        
        Args:
            rpath: 设备上的文件路径
            lpath: 本地保存路径
            
        Returns:
            CommandResult: 命令执行结果
            
        Raises:
            HdcError: 接收文件失败时抛出
        """
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} file recv {rpath} {lpath}")
        if result.exit_code != 0:
            raise HdcError("HDC 接收文件错误", result.error)
        return result

    def shell(self, cmd: str, error_raise: bool = True) -> CommandResult:
        """
        在设备上执行 Shell 命令
        
        Args:
            cmd: 要执行的 Shell 命令
            error_raise: 命令失败时是否抛出异常，默认为 True
            
        Returns:
            CommandResult: 命令执行结果
            
        Raises:
            HdcError: 命令执行失败且 error_raise 为 True 时抛出
        """
        # 确保命令用双引号包裹
        if cmd[0] != '\"':
            cmd = "\"" + cmd
        if cmd[-1] != '\"':
            cmd += '\"'
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} shell {cmd}")
        if result.exit_code != 0 and error_raise:
            raise HdcError("HDC Shell 命令错误", f"{cmd}\n{result.output}\n{result.error}")
        return result

    def uninstall(self, bundlename: str) -> CommandResult:
        """
        卸载应用
        
        Args:
            bundlename: 应用包名
            
        Returns:
            CommandResult: 命令执行结果
            
        Raises:
            HdcError: 卸载应用失败时抛出
        """
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} uninstall {bundlename}")
        if result.exit_code != 0:
            raise HdcError("HDC 卸载应用错误", result.output)
        return result

    def install(self, apkpath: str) -> CommandResult:
        """
        安装应用
        
        Args:
            apkpath: 应用安装包路径
            
        Returns:
            CommandResult: 命令执行结果
            
        Raises:
            HdcError: 安装应用失败时抛出
        """
        # 确保路径正确引用，特别是在 Windows 系统上
        quoted_path = f'"{apkpath}"'

        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} install {quoted_path}")
        if result.exit_code != 0:
            raise HdcError("HDC 安装应用错误", result.error)
        return result

    def list_apps(self) -> List[str]:
        """
        列出设备上的所有应用
        
        Returns:
            List[str]: 应用列表
        """
        result = self.shell("bm dump -a")
        raw = result.output.split('\n')
        return [item.strip() for item in raw if item.strip()]

    def has_app(self, package_name: str) -> bool:
        """
        检查设备上是否安装了指定应用
        
        Args:
            package_name: 应用包名
            
        Returns:
            bool: 应用存在返回 True，否则返回 False
        """
        data = self.shell("bm dump -a").output
        return package_name in data

    def start_app(self, package_name: str, ability_name: str) -> CommandResult:
        """
        启动应用
        
        Args:
            package_name: 应用包名
            ability_name: Ability 名称
            
        Returns:
            CommandResult: 命令执行结果
        """
        return self.shell(f"aa start -a {ability_name} -b {package_name}")

    def stop_app(self, package_name: str) -> CommandResult:
        """
        停止应用
        
        Args:
            package_name: 应用包名
            
        Returns:
            CommandResult: 命令执行结果
        """
        return self.shell(f"aa force-stop {package_name}")

    def current_app(self) -> Tuple[Optional[str], Optional[str]]:
        """
        获取当前前台应用信息
        
        Returns:
            Tuple[Optional[str], Optional[str]]: 包含应用包名和页面名称的元组
                                                如果未找到前台应用，返回 (None, None)
        """
        def __extract_info(output: str) -> List[Tuple[str, str]]:
            """提取应用信息"""
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

    def wakeup(self) -> None:
        """唤醒设备"""
        self.shell("power-shell wakeup")

    def screen_state(self) -> Optional[str]:
        """
        获取屏幕状态
        
        Returns:
            Optional[str]: 屏幕状态，可能的值包括 "INACTIVE"、"SLEEP"、"AWAKE" 等
                          如果无法获取状态，返回 None
        """
        data = self.shell("hidumper -s PowerManagerService -a -s").output
        pattern = r"Current State:\s*(\w+)"
        match = re.search(pattern, data)

        return match.group(1) if match else None

    def wlan_ip(self) -> Optional[str]:
        """
        获取设备的 WLAN IP 地址
        
        Returns:
            Optional[str]: WLAN IP 地址，如果未找到则返回 None
        """
        data = self.shell("ifconfig").output
        matches = re.findall(r'inet addr:(?!127)(\d+\.\d+\.\d+\.\d+)', data)
        return matches[0] if matches else None

    def __split_text(self, text: Optional[str]) -> Optional[str]:
        """
        从文本中提取第一行并去除前后空白
        
        Args:
            text: 输入文本
            
        Returns:
            Optional[str]: 处理后的文本，如果输入为 None 则返回 None
        """
        return text.split("\n")[0].strip() if text else None

    def sdk_version(self) -> Optional[str]:
        """
        获取设备 SDK 版本
        
        Returns:
            Optional[str]: SDK 版本
        """
        data = self.shell("param get const.ohos.apiversion").output
        return self.__split_text(data)

    def sys_version(self) -> Optional[str]:
        """
        获取设备系统版本
        
        Returns:
            Optional[str]: 系统版本
        """
        data = self.shell("param get const.product.software.version").output
        return self.__split_text(data)

    def model(self) -> Optional[str]:
        """
        获取设备型号
        
        Returns:
            Optional[str]: 设备型号
        """
        data = self.shell("param get const.product.model").output
        return self.__split_text(data)

    def brand(self) -> Optional[str]:
        """
        获取设备品牌
        
        Returns:
            Optional[str]: 设备品牌
        """
        data = self.shell("param get const.product.brand").output
        return self.__split_text(data)

    def product_name(self) -> Optional[str]:
        """
        获取设备产品名称
        
        Returns:
            Optional[str]: 产品名称
        """
        data = self.shell("param get const.product.name").output
        return self.__split_text(data)

    def cpu_abi(self) -> Optional[str]:
        """
        获取设备 CPU ABI
        
        Returns:
            Optional[str]: CPU ABI
        """
        data = self.shell("param get const.product.cpu.abilist").output
        return self.__split_text(data)

    def display_size(self) -> Tuple[int, int]:
        """
        获取设备屏幕尺寸
        
        Returns:
            Tuple[int, int]: 屏幕宽度和高度，如果无法获取则返回 (0, 0)
        """
        data = self.shell("hidumper -s RenderService -a screen").output
        match = re.search(r'activeMode:\s*(\d+)x(\d+),\s*refreshrate=\d+', data)

        if match:
            w = int(match.group(1))
            h = int(match.group(2))
            return (w, h)
        return (0, 0)

    def send_key(self, key_code: Union[KeyCode, int]) -> None:
        """
        发送按键事件
        
        Args:
            key_code: 按键代码，可以是 KeyCode 枚举或整数
            
        Raises:
            HdcError: 按键代码无效时抛出
        """
        if isinstance(key_code, KeyCode):
            key_code = key_code.value

        if key_code > MAX_KEY_CODE:
            raise HdcError("无效的 HDC 按键代码")

        self.shell(f"uitest uiInput keyEvent {key_code}")

    def tap(self, x: int, y: int) -> None:
        """
        点击屏幕
        
        Args:
            x: X 坐标
            y: Y 坐标
        """
        self.shell(f"uitest uiInput click {x} {y}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, speed: int = 1000) -> None:
        """
        在屏幕上滑动
        
        Args:
            x1: 起始 X 坐标
            y1: 起始 Y 坐标
            x2: 结束 X 坐标
            y2: 结束 Y 坐标
            speed: 滑动速度，默认为 1000
        """
        self.shell(f"uitest uiInput swipe {x1} {y1} {x2} {y2} {speed}")

    def input_text(self, x: int, y: int, text: str) -> None:
        """
        在指定位置输入文本
        
        Args:
            x: X 坐标
            y: Y 坐标
            text: 要输入的文本
        """
        self.shell(f"uitest uiInput inputText {x} {y} {text}")

    def screenshot(self, path: str) -> str:
        """
        截取屏幕
        
        Args:
            path: 本地保存路径
            
        Returns:
            str: 截图保存路径
        """
        _uuid = uuid.uuid4().hex
        _tmp_path = f"/data/local/tmp/_tmp_{_uuid}.jpeg"
        self.shell(f"snapshot_display -f {_tmp_path}")
        self.recv_file(_tmp_path, path)
        self.shell(f"rm -rf {_tmp_path}")  # 删除临时文件
        return path

    def dump_hierarchy(self) -> Dict[str, Any]:
        """
        导出界面层次结构
        
        Returns:
            Dict[str, Any]: 界面层次结构数据，如果解析失败则返回空字典
        """
        _tmp_path = f"/data/local/tmp/{self.serial}_tmp.json"
        self.shell(f"uitest dumpLayout -p {_tmp_path}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            path = f.name
            self.recv_file(_tmp_path, path)

            try:
                with open(path, 'r', encoding='utf8') as file:
                    data = json.load(file)
            except Exception as e:
                logger.error(f"加载 JSON 文件时出错: {e}")
                data = {}

            return data
