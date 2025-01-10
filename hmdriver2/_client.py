# -*- coding: utf-8 -*-
import socket
import json
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
        msg = json.dumps(msg, ensure_ascii=False, separators=(',', ':'))
        logger.debug(f"sendMsg: {msg}")
        self.sock.sendall(msg.encode('utf-8') + b'\n')

    def _recv_msg(self, buff_size: int = 4096, decode=False, print=True) -> typing.Union[bytearray, str]:
        full_msg = bytearray()
        try:
            # FIXME
            relay = self.sock.recv(buff_size)
            if decode:
                relay = relay.decode()
            if print:
                logger.debug(f"recvMsg: {relay}")
            full_msg = relay

        except (socket.timeout, UnicodeDecodeError) as e:
            logger.warning(e)
            if decode:
                full_msg = ""

        return full_msg

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
        """Return the local path of the agent file."""
        target_agent = "uitest_agent_v1.1.0.so"
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