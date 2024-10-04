# -*- coding: utf-8 -*-

import socket
import json
import time
import os
import typing
import subprocess
import hashlib
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
        self._init_so_resource()
        self._restart_uitest_service()

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
        logger.debug("create uitest driver")
        resp: HypiumResponse = self.invoke("Driver.create")  # {"result":"Driver#0"}
        hdriver: DriverData = DriverData(resp.result)
        return hdriver

    def _init_so_resource(self):
        "Initialize the agent.so resource on the device."

        logger.debug("init the agent.so resource on the device.")

        def __get_so_local_path() -> str:
            current_path = os.path.realpath(__file__)
            return os.path.join(os.path.dirname(current_path), "assets", "agent.so")

        def __check_device_so_file_exists() -> bool:
            """Check if the agent.so file exists on the device."""
            command = "[ -f /data/local/tmp/agent.so ] && echo 'so exists' || echo 'so not exists'"
            result = self.hdc.shell(command).output.strip()
            return "so exists" in result

        def __get_remote_md5sum() -> str:
            """Get the MD5 checksum of the file on the device."""
            command = "md5sum /data/local/tmp/agent.so"
            data = self.hdc.shell(command).output.strip()
            return data.split()[0]

        def __get_local_md5sum(f: str) -> str:
            """Calculate the MD5 checksum of a local file."""
            hash_md5 = hashlib.md5()
            with open(f, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()

        local_path = __get_so_local_path()
        remote_path = "/data/local/tmp/agent.so"

        if __check_device_so_file_exists() and __get_local_md5sum(local_path) == __get_remote_md5sum():
            return
        self.hdc.send_file(local_path, remote_path)
        self.hdc.shell(f"chmod +x {remote_path}")

    def _restart_uitest_service(self):
        """
        Restart the UITest daemon.

        Note: 'hdc shell aa test' will also start a uitest daemon.
        $ hdc shell ps -ef |grep uitest
        shell        44306     1 25 11:03:37 ?    00:00:16 uitest start-daemon singleness
        shell        44416     1 2 11:03:42 ?     00:00:01 uitest start-daemon com.hmtest.uitest@4x9@1"
        """
        try:
            result = self.hdc.shell("ps -ef").output.strip()
            lines = result.splitlines()
            filtered_lines = [line for line in lines if 'uitest' in line and 'singleness' in line]

            for line in filtered_lines:
                if 'uitest start-daemon singleness' in line:
                    parts = line.split()
                    pid = parts[1]
                    self.hdc.shell(f"kill -9 {pid}")
                    logger.debug(f"Killed uitest process with PID {pid}")

            self.hdc.shell("uitest start-daemon singleness")
            time.sleep(.5)

        except subprocess.CalledProcessError as e:
            logger.error(f"An error occurred: {e}")
