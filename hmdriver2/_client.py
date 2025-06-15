# -*- coding: utf-8 -*-

import hashlib
import json
import os
import socket
import struct
import time
from datetime import datetime
from functools import cached_property
from typing import Optional, Union, Dict, List, Any

from . import logger
from .exception import InvokeHypiumError, InvokeCaptures
from .hdc import HdcWrapper
from .proto import HypiumResponse, DriverData

# 连接相关常量
UITEST_SERVICE_PORT = 8012  # 设备端服务端口
SOCKET_TIMEOUT = 20         # Socket 超时时间（秒）
LOCAL_HOST = "127.0.0.1"    # 本地主机地址

# 消息协议常量
MSG_HEADER = b'_uitestkit_rpc_message_head_'  # 消息头标识
MSG_TAILER = b'_uitestkit_rpc_message_tail_'  # 消息尾标识
SESSION_ID_LENGTH = 4                          # 会话ID长度（字节）

# API 模块常量
API_MODULE = "com.ohos.devicetest.hypiumApiHelper"  # API 模块名
API_METHOD_HYPIUM = "callHypiumApi"                 # Hypium API 调用方法
API_METHOD_CAPTURES = "Captures"                    # Captures API 调用方法
DEFAULT_THIS = "Driver#0"                           # 默认目标对象


class HmClient:
    """
    Harmony OS 设备通信客户端
    
    负责与设备建立连接、发送命令和接收响应，是与设备交互的基础类。
    通过 HDC（Harmony Debug Console）建立端口转发，使用 Socket 进行通信。
    """

    def __init__(self, serial: str):
        """
        初始化客户端
        
        Args:
            serial: 设备序列号
        """
        self.hdc = HdcWrapper(serial)
        self.sock: Optional[socket.socket] = None
        self._header_length = len(MSG_HEADER)
        self._tailer_length = len(MSG_TAILER)

    @cached_property
    def local_port(self) -> int:
        """
        获取本地转发端口
        
        Returns:
            int: 本地端口号
        """
        fports = self.hdc.list_fport()
        if fports:
            logger.debug(fports)
        return self.hdc.forward_port(UITEST_SERVICE_PORT)

    def _rm_local_port(self) -> None:
        """移除本地端口转发"""
        logger.debug("移除本地端口转发")
        self.hdc.rm_forward(self.local_port, UITEST_SERVICE_PORT)

    def _connect_sock(self) -> None:
        """创建 Socket 并连接到 UITest 服务器"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(SOCKET_TIMEOUT)
        self.sock.connect((LOCAL_HOST, self.local_port))

    def _send_msg(self, msg: Dict[str, Any]) -> None:
        """
        发送消息到服务器
        
        Args:
            msg: 要发送的消息字典
            
        消息格式示例:
        {
            "module": "com.ohos.devicetest.hypiumApiHelper",
            "method": "callHypiumApi",
            "params": {
                "api": "Driver.create",
                "this": null,
                "args": [],
                "message_type": "hypium"
            },
            "request_id": "20240815161352267072"
        }
        """
        # 序列化消息
        msg_str = json.dumps(msg, ensure_ascii=False, separators=(',', ':'))
        logger.debug(f"发送消息: {msg_str}")

        # 生成会话ID并构建消息头
        msg_bytes = msg_str.encode('utf-8')
        session_id = self._generate_session_id(msg_str)
        header = (
            MSG_HEADER +
            struct.pack('>I', session_id) +
            struct.pack('>I', len(msg_bytes))
        )

        # 发送完整消息（头部 + 消息体 + 尾部）
        if self.sock is None:
            raise ConnectionError("Socket 未连接")
        self.sock.sendall(header + msg_bytes + MSG_TAILER)

    def _generate_session_id(self, message: str) -> int:
        """
        生成会话ID
        
        将时间戳、消息内容和随机数据组合生成唯一标识符
        
        Args:
            message: 消息内容
            
        Returns:
            int: 生成的会话ID
        """
        # 组合时间戳、消息内容和随机数据
        combined = (
            str(int(time.time() * 1000)) +  # 毫秒时间戳
            message +
            os.urandom(4).hex()  # 16字节随机熵
        )
        # 生成哈希并取前8位转为整数
        return int(hashlib.sha256(combined.encode()).hexdigest()[:8], 16)

    def _recv_msg(self, decode: bool = False, print: bool = True) -> Union[bytearray, str]:
        """
        接收并解析消息
        
        Args:
            decode: 是否解码为字符串
            print: 是否打印接收到的消息
            
        Returns:
            解析后的消息内容（字节数组或字符串）
            
        Raises:
            ConnectionError: 连接中断时抛出
        """
        try:
            # 接收消息头
            header_len = self._header_length + SESSION_ID_LENGTH + 4
            header = self._recv_exact(header_len)  # 头部 + session_id + length
            if not header or header[:self._header_length] != MSG_HEADER:
                logger.warning("接收到无效的消息头")
                return bytearray() if not decode else ""

            # 解析消息长度（不验证session_id）
            msg_length = struct.unpack('>I', header[self._header_length + SESSION_ID_LENGTH:])[0]

            # 接收消息体
            msg_bytes = self._recv_exact(msg_length)
            if not msg_bytes:
                logger.warning("接收消息体失败")
                return bytearray() if not decode else ""

            # 接收消息尾
            tailer = self._recv_exact(self._tailer_length)
            if not tailer or tailer != MSG_TAILER:
                logger.warning("接收到无效的消息尾")
                return bytearray() if not decode else ""

            # 处理消息内容
            if not decode:
                logger.debug(f"接收到字节消息 (大小: {len(msg_bytes)})")
                return bytearray(msg_bytes)

            # 解码为字符串
            msg_str = msg_bytes.decode('utf-8')
            if print:
                logger.debug(f"接收到消息: {msg_str}")
            return msg_str

        except (socket.timeout, ValueError, json.JSONDecodeError) as e:
            logger.warning(f"接收消息时出错: {e}")
            return bytearray() if not decode else ""

    def _recv_exact(self, length: int) -> bytes:
        """
        精确接收指定长度的数据
        
        使用内存视图优化接收性能，确保接收完整数据
        
        Args:
            length: 要接收的数据长度
            
        Returns:
            bytes: 接收到的数据
            
        Raises:
            ConnectionError: 连接关闭时抛出
        """
        if self.sock is None:
            raise ConnectionError("Socket 未连接")
            
        buf = bytearray(length)
        view = memoryview(buf)
        pos = 0

        while pos < length:
            chunk_size = self.sock.recv_into(view[pos:], length - pos)
            if not chunk_size:
                raise ConnectionError("接收数据时连接已关闭")
            pos += chunk_size

        return buf

    def invoke(self, api: str, this: Optional[str] = DEFAULT_THIS, args: Optional[List[Any]] = None) -> HypiumResponse:
        """
        调用 Hypium API
        
        Args:
            api: API 名称
            this: 目标对象标识符，默认为 "Driver#0"
            args: API 参数列表，默认为空列表
            
        Returns:
            HypiumResponse: API 调用响应
            
        Raises:
            InvokeHypiumError: API 调用返回异常时抛出
        """
        if args is None:
            args = []

        # 构建请求参数
        request_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        params = {
            "api": api,
            "this": this,
            "args": args,
            "message_type": "hypium"
        }

        # 构建完整消息
        msg = {
            "module": API_MODULE,
            "method": API_METHOD_HYPIUM,
            "params": params,
            "request_id": request_id
        }

        # 发送请求并处理响应
        self._send_msg(msg)
        raw_data = self._recv_msg(decode=True)
        if not raw_data:
            raise InvokeHypiumError("接收响应失败")
            
        try:
            data = HypiumResponse(**(json.loads(raw_data)))
        except json.JSONDecodeError as e:
            raise InvokeHypiumError(f"解析响应失败: {e}")
        
        # 处理异常
        if data.exception:
            raise InvokeHypiumError(data.exception)
        return data

    def invoke_captures(self, api: str, args: Optional[List[Any]] = None) -> HypiumResponse:
        """
        调用 Captures API
        
        Args:
            api: API 名称
            args: API 参数列表，默认为空列表
            
        Returns:
            HypiumResponse: API 调用响应
            
        Raises:
            InvokeCaptures: API 调用返回异常时抛出
        """
        if args is None:
            args = []

        # 构建请求参数
        request_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        params = {
            "api": api,
            "args": args
        }

        # 构建完整消息
        msg = {
            "module": API_MODULE,
            "method": API_METHOD_CAPTURES,
            "params": params,
            "request_id": request_id
        }

        # 发送请求并处理响应
        self._send_msg(msg)
        raw_data = self._recv_msg(decode=True)
        if not raw_data:
            raise InvokeCaptures("接收响应失败")
            
        try:
            data = HypiumResponse(**(json.loads(raw_data)))
        except json.JSONDecodeError as e:
            raise InvokeCaptures(f"解析响应失败: {e}")
        
        # 处理异常
        if data.exception:
            raise InvokeCaptures(data.exception)
        return data

    def start(self) -> None:
        """
        启动客户端连接
        
        初始化 UITest 服务，建立 Socket 连接，创建驱动实例
        """
        logger.info("启动 HmClient 连接")
        _UITestService(self.hdc).init()
        self._connect_sock()
        self._create_hdriver()

    def release(self) -> None:
        """
        释放客户端资源
        
        关闭 Socket 连接，移除端口转发
        """
        logger.info(f"释放 {self.__class__.__name__} 连接")
        try:
            if self.sock:
                self.sock.close()
                self.sock = None

            self._rm_local_port()

        except Exception as e:
            logger.error(f"释放资源时出错: {e}")

    def _create_hdriver(self) -> DriverData:
        """
        创建 UITest 驱动实例
        
        Returns:
            DriverData: 驱动数据对象
        """
        logger.debug("创建 UITest 驱动")
        resp: HypiumResponse = self.invoke("Driver.create")  # {"result":"Driver#0"}
        hdriver: DriverData = DriverData(resp.result)
        return hdriver


class _UITestService:
    """
    UITest 服务管理类
    
    负责初始化设备上的 UITest 服务，包括安装必要的库文件和启动服务进程
    """

    def __init__(self, hdc: HdcWrapper):
        """
        初始化 UITest 服务管理类
        
        Args:
            hdc: HDC 包装器实例
        """
        self.hdc = hdc
        self._remote_agent_path = "/data/local/tmp/agent.so"

    def init(self) -> None:
        """
        初始化 UITest 服务
        
        1. 确保设备上安装了 agent.so
        2. 启动 UITest 守护进程
        
        Note:
            'hdc shell aa test' 也会启动 UITest 守护进程
            $ hdc shell ps -ef |grep uitest
            shell        44306     1 25 11:03:37 ?    00:00:16 uitest start-daemon singleness
            shell        44416     1 2 11:03:42 ?     00:00:01 uitest start-daemon com.hmtest.uitest@4x9@1"
        """
        logger.debug("初始化 UITest 服务")
        local_path = self._get_local_agent_path()

        # 按顺序执行初始化步骤
        self._kill_uitest_service()  # 停止可能运行的服务
        self._setup_device_agent(local_path, self._remote_agent_path)
        self._start_uitest_daemon()
        time.sleep(0.5)  # 等待服务启动

    def _get_local_agent_path(self) -> str:
        """
        获取本地 agent.so 文件路径
        
        根据设备 CPU 架构选择对应的库文件
        
        Returns:
            str: 本地 agent.so 文件路径
        """
        cpu_abi = self.hdc.cpu_abi()
        target_agent = os.path.join("so", cpu_abi, "agent.so")
        return os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets", target_agent)

    def _get_remote_md5sum(self, file_path: str) -> Optional[str]:
        """
        获取远程文件的 MD5 校验和
        
        Args:
            file_path: 远程文件路径
            
        Returns:
            Optional[str]: MD5 校验和，如果文件不存在则返回 None
        """
        command = f"md5sum {file_path}"
        output = self.hdc.shell(command).output.strip()
        return output.split()[0] if output else None

    def _get_local_md5sum(self, file_path: str) -> str:
        """
        获取本地文件的 MD5 校验和
        
        Args:
            file_path: 本地文件路径
            
        Returns:
            str: MD5 校验和
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _is_remote_file_exists(self, file_path: str) -> bool:
        """
        检查远程文件是否存在
        
        Args:
            file_path: 远程文件路径
            
        Returns:
            bool: 文件存在返回 True，否则返回 False
        """
        command = f"[ -f {file_path} ] && echo 'exists' || echo 'not exists'"
        result = self.hdc.shell(command).output.strip()
        return "exists" in result

    def _setup_device_agent(self, local_path: str, remote_path: str) -> None:
        """
        设置设备上的 agent.so 文件
        
        如果远程文件不存在或与本地文件不一致，则上传本地文件
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
        """
        # 检查远程文件是否存在且与本地文件一致
        if self._is_remote_file_exists(remote_path):
            local_md5 = self._get_local_md5sum(local_path)
            remote_md5 = self._get_remote_md5sum(remote_path)
            if local_md5 == remote_md5:
                logger.debug("远程 agent 文件已是最新")
                self.hdc.shell(f"chmod +x {remote_path}")
                return
            self.hdc.shell(f"rm {remote_path}")

        # 上传并设置权限
        self.hdc.send_file(local_path, remote_path)
        self.hdc.shell(f"chmod +x {remote_path}")
        logger.debug("已更新远程 agent 文件")

    def _get_uitest_pid(self) -> List[str]:
        """
        获取 UITest 守护进程的 PID 列表
        
        Returns:
            List[str]: PID 列表
        """
        proc_pids = []
        result = self.hdc.shell("ps -ef").output.strip()
        lines = result.splitlines()
        filtered_lines = [line for line in lines if 'uitest' in line and 'singleness' in line]
        for line in filtered_lines:
            if 'uitest start-daemon singleness' not in line:
                continue
            proc_pids.append(line.split()[1])
        return proc_pids

    def _kill_uitest_service(self) -> None:
        """终止所有 UITest 守护进程"""
        for pid in self._get_uitest_pid():
            self.hdc.shell(f"kill -9 {pid}")
            logger.debug(f"已终止 UITest 进程，PID: {pid}")

    def _start_uitest_daemon(self) -> None:
        """启动 UITest 守护进程"""
        self.hdc.shell("uitest start-daemon singleness")
        logger.debug("已启动 UITest 守护进程")
