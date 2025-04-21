# -*- coding: utf-8 -*-
import socket
import json
import struct
import time
import os
import hashlib
import typing
from typing import Optional
from datetime import datetime
from functools import cached_property

from . import logger
from .hdc import HdcWrapper
from .proto import HypiumResponse, DriverData
from .exception import InvokeHypiumError, InvokeCaptures


UITEST_SERVICE_PORT = 8012
SOCKET_TIMEOUT = 20


class HmClient:
    HEADER_BYTES = b'_uitestkit_rpc_message_head_'
    TAILER_BYTES = b'_uitestkit_rpc_message_tail_'
    HEADER_LENGTH = len(HEADER_BYTES)
    TAILER_LENGTH = len(TAILER_BYTES)
    SESSION_ID_LENGTH = 4  # 4 bytes for session ID

    """harmony uitest client"""
    def __init__(self, serial: str):
        self.hdc = HdcWrapper(serial)
        self.sock = None

    @cached_property
    def local_port(self):
        fports = self.hdc.list_fport()
        logger.debug(fports) if fports else None

        return self.hdc.forward_port(UITEST_SERVICE_PORT)

    def _rm_local_port(self):
        logger.debug("rm fport local port")
        self.hdc.rm_forward(self.local_port, UITEST_SERVICE_PORT)

    def _connect_sock(self):
        """Create socket and connect to the uiTEST server."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(SOCKET_TIMEOUT)
        self.sock.connect((("127.0.0.1", self.local_port)))

    def _send_msg(self, msg: typing.Dict):
        """Send an message to the server.
        Example:
            {
                "module": "com.ohos.devicetest.hypiumApiHelper",
                "method": "callHypiumApi",
                "params": {
                    "api": "Driver.create",
                    "this": null,
                    "args": [],
                    "message_type": "hypium"
                },
                "request_id": "20240815161352267072",
                "client": "127.0.0.1"
            }
        """
        msg_str = json.dumps(msg, ensure_ascii=False, separators=(',', ':'))
        logger.debug(f"sendMsg: {msg_str}")

        # 生成 session_id
        msg_bytes = msg_str.encode('utf-8')
        session_id = self._generate_session_id(msg_str)
        header = (
                self.HEADER_BYTES +
                struct.pack('>I', session_id) +
                struct.pack('>I', len(msg_bytes))
        )

        # 发送完整消息
        self.sock.sendall(header + msg_bytes + self.TAILER_BYTES)

    def _generate_session_id(self, message: str) -> int:
        """
        生成 sessionId 的逻辑，将时间戳、消息字符串拼接后生成整数哈希值。
        """
        # 拼接时间戳和消息字符串，添加随机熵
        combined = (
                str(int(time.time() * 1000)) +  # 毫秒时间戳
                message +
                os.urandom(4).hex()  # 16字节随机熵
        )
        return int(hashlib.sha256(combined.encode()).hexdigest()[:8], 16)

    def _recv_msg(self, decode=False, print=True) -> typing.Union[bytearray, str]:
        """
        接收消息，解析请求头和尾部，返回消息内容。
        """
        try:
            # 接收头部
            header_len = self.HEADER_LENGTH + self.SESSION_ID_LENGTH + 4
            header = self._recv_exact(header_len) # 头部 + session_id + length
            if not header or header[:len(self.HEADER_BYTES)] != self.HEADER_BYTES:
                logger.warning("Invalid header received")
                return ""

            # 解析消息长度（目前无需验证session_id，所以不做处理）
            msg_length = struct.unpack('>I', header[self.HEADER_LENGTH + self.SESSION_ID_LENGTH:])[0]  # 大端序

            # 接收消息体
            msg_bytes = self._recv_exact(msg_length)
            if not msg_bytes:
                logger.warning("Failed to receive message body")
                return ""

            # 接收尾部
            tailer = self._recv_exact(self.TAILER_LENGTH)
            if not tailer or tailer != self.TAILER_BYTES:
                logger.warning("Invalid tailer received")
                return ""

            # 解码消息
            if not decode:
                logger.debug(f"recvMsg byte message (size: %d)", len(msg_bytes))
                return bytearray(msg_bytes)

            msg_str = msg_bytes.decode('utf-8')
            if print:
                logger.debug(f"recvMsg: {msg_str}")
            return msg_str

        except (socket.timeout, ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Error receiving message: {e}")
            return ""

    def _recv_exact(self, length: int) -> bytes:
        """
        确保接收指定长度的数据。
        """
        buf = bytearray(length)
        view = memoryview(buf)
        pos = 0

        while pos < length:
            chunk_size = self.sock.recv_into(view[pos:], length - pos)
            if not chunk_size:
                raise ConnectionError("Connection closed during receive")
            pos += chunk_size

        return buf

    def invoke(self, api: str, this: str = "Driver#0", args: typing.List = []) -> HypiumResponse:
        """
        Hypium invokes given API method with the specified arguments and handles exceptions.

        Args:
        api (str): The name of the API method to invoke.
        args (List, optional): A list of arguments to pass to the API method. Default is an empty list.

        Returns:
        HypiumResponse: The response from the API call.

        Raises:
        InvokeHypiumError: If the API call returns an exception in the response.
        """

        request_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        params = {
            "api": api,
            "this": this,
            "args": args,
            "message_type": "hypium"
        }

        msg = {
            "module": "com.ohos.devicetest.hypiumApiHelper",
            "method": "callHypiumApi",
            "params": params,
            "request_id": request_id
        }

        self._send_msg(msg)
        raw_data = self._recv_msg(decode=True)
        data = HypiumResponse(**(json.loads(raw_data)))
        if data.exception:
            raise InvokeHypiumError(data.exception)
        return data

    def invoke_captures(self, api: str, args: typing.List = []) -> HypiumResponse:
        request_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        params = {
            "api": api,
            "args": args
        }

        msg = {
            "module": "com.ohos.devicetest.hypiumApiHelper",
            "method": "Captures",
            "params": params,
            "request_id": request_id
        }

        self._send_msg(msg)
        raw_data = self._recv_msg(decode=True)
        data = HypiumResponse(**(json.loads(raw_data)))
        if data.exception:
            raise InvokeCaptures(data.exception)
        return data

    def start(self):
        logger.info("Start HmClient connection")
        _UITestService(self.hdc).init()

        self._connect_sock()

        self._create_hdriver()

    def release(self):
        logger.info(f"Release {self.__class__.__name__} connection")
        try:
            if self.sock:
                self.sock.close()
                self.sock = None

            self._rm_local_port()

        except Exception as e:
            logger.error(f"An error occurred: {e}")

    def _create_hdriver(self) -> DriverData:
        logger.debug("Create uitest driver")
        resp: HypiumResponse = self.invoke("Driver.create")  # {"result":"Driver#0"}
        hdriver: DriverData = DriverData(resp.result)
        return hdriver


class _UITestService:
    def __init__(self, hdc: HdcWrapper):
        """Initialize the UITestService class."""
        self.hdc = hdc

    def init(self):
        """
        Initialize the UITest service:
        1. Ensure agent.so is set up on the device.
        2. Start the UITest daemon.

        Note: 'hdc shell aa test' will also start a uitest daemon.
        $ hdc shell ps -ef |grep uitest
        shell        44306     1 25 11:03:37 ?    00:00:16 uitest start-daemon singleness
        shell        44416     1 2 11:03:42 ?     00:00:01 uitest start-daemon com.hmtest.uitest@4x9@1"
        """

        logger.debug("Initializing UITest service")
        local_path = self._get_local_agent_path()
        remote_path = "/data/local/tmp/agent.so"

        self._kill_uitest_service()  # Stop the service if running
        self._setup_device_agent(local_path, remote_path)
        self._start_uitest_daemon()
        time.sleep(0.5)

    def _get_local_agent_path(self) -> str:
        """Return the local path of the agent file, based on the cpu_abi version (e.g., 'so/arm64-v8a/agent.so')."""
        cpu_abi = self.hdc.cpu_abi()

        target_agent = os.path.join("so", cpu_abi, "agent.so")
        return os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets", target_agent)

    def _get_remote_md5sum(self, file_path: str) -> Optional[str]:
        """Get the MD5 checksum of a remote file."""
        command = f"md5sum {file_path}"
        output = self.hdc.shell(command).output.strip()
        return output.split()[0] if output else None

    def _get_local_md5sum(self, file_path: str) -> str:
        """Get the MD5 checksum of a local file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _is_remote_file_exists(self, file_path: str) -> bool:
        """Check if a file exists on the device."""
        command = f"[ -f {file_path} ] && echo 'exists' || echo 'not exists'"
        result = self.hdc.shell(command).output.strip()
        return "exists" in result

    def _setup_device_agent(self, local_path: str, remote_path: str):
        """Ensure the remote agent file is correctly set up."""
        if self._is_remote_file_exists(remote_path):
            local_md5 = self._get_local_md5sum(local_path)
            remote_md5 = self._get_remote_md5sum(remote_path)
            if local_md5 == remote_md5:
                logger.debug("Remote agent file is up-to-date")
                self.hdc.shell(f"chmod +x {remote_path}")
                return
            self.hdc.shell(f"rm {remote_path}")

        self.hdc.send_file(local_path, remote_path)
        self.hdc.shell(f"chmod +x {remote_path}")
        logger.debug("Updated remote agent file")

    def _get_uitest_pid(self) -> typing.List[str]:
        proc_pids = []
        result = self.hdc.shell("ps -ef").output.strip()
        lines = result.splitlines()
        filtered_lines = [line for line in lines if 'uitest' in line and 'singleness' in line]
        for line in filtered_lines:
            if 'uitest start-daemon singleness' not in line:
                continue
            proc_pids.append(line.split()[1])
        return proc_pids

    def _kill_uitest_service(self):
        for pid in self._get_uitest_pid():
            self.hdc.shell(f"kill -9 {pid}")
            logger.debug(f"Killed uitest process with PID {pid}")

    def _start_uitest_daemon(self):
        """Start the UITest daemon."""
        self.hdc.shell("uitest start-daemon singleness")
        logger.debug("Started UITest daemon")