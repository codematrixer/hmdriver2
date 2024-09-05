# -*- coding: utf-8 -*-

import socket
import json
import time
import os
import typing
import subprocess
import atexit
import hashlib
from datetime import datetime
from functools import cached_property

from . import logger
from .hdc import HdcWrapper
from .proto import HypiumResponse, DriverData


UITEST_SERICE_PORT = 8012
SOCKET_TIMEOUT = 60


class HMClient:
    """harmony uitest client"""
    def __init__(self, serial: str):
        self.hdc = HdcWrapper(serial)
        self.sock = None

        self.start()

        self._hdriver: DriverData = self._create_hdriver()

    @cached_property
    def local_port(self):
        fports = self.hdc.list_fport()
        logger.debug(fports) if fports else None

        return self.hdc.forward_port(UITEST_SERICE_PORT)

    def _rm_local_port(self):
        logger.debug("rm fport local port")
        self.hdc.rm_forward(self.local_port, UITEST_SERICE_PORT)

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

    def _recv_msg(self, buff_size: int = 1024, decode=False) -> typing.Union[bytearray, str]:
        try:
            relay = self.sock.recv(buff_size)
            if decode:
                relay = relay.decode()
            logger.debug(f"recvMsg: {relay}")
            return relay
        except (socket.timeout, UnicodeDecodeError) as e:
            logger.warning(e)
            if decode:
                return ''
            return bytearray()

    def invoke(self, api: str, this: str = "Driver#0", args: typing.List = []) -> HypiumResponse:
        msg = {
            "module": "com.ohos.devicetest.hypiumApiHelper",
            "method": "callHypiumApi",
            "params": {
                "api": api,
                "this": this,
                "args": args,
                "message_type": "hypium"
            },
            "request_id": datetime.now().strftime("%Y%m%d%H%M%S%f")
        }
        self._send_msg(msg)
        result = self._recv_msg(decode=True)
        # TODO handle exception
        # {"exception":{"code":401,"message":"(PreProcessing: APiCallInfoChecker)Illegal argument count"}}

        return HypiumResponse(**(json.loads(result)))

    def start(self):
        logger.info("Start client connection")
        self._init_so_resource()
        self._restart_uitest_service()

        self._connect_sock()

    def release(self):
        logger.info("Release client connection")
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
            return os.path.join(os.path.dirname(current_path), "asset", "agent.so")

        def __check_device_so_file_exists() -> bool:
            """Check if the agent.so file exists on the device."""
            command = "[ -f /data/local/tmp/agent.so ] && echo 'so exists' || echo 'so not exists'"
            result = self.hdc.shell(command).output.strip()
            return "so exists" in result

        def __get_remote_md5sum() -> str:
            """Get the MD5 checksum of the file on the device."""
            command = "md5sum /data/local/tmp/agent.so | awk '{ print $1 }'"
            result = self.hdc.shell(command).output.strip()
            return result

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

    def _restart_uitest_service(self):
        """
        Restart the UITest daemon.

        Note: 'hdc shell aa test' will also start a uitest daemon.
        $ hdc shell ps -ef |grep uitest
        shell        44306     1 25 11:03:37 ?    00:00:16 uitest start-daemon singleness
        shell        44416     1 2 11:03:42 ?     00:00:01 uitest start-daemon com.hmtest.uitest@4x9@1"
        """
        try:
            # pids: list = self.hdc.shell("pidof uitest").output.strip().split()
            result = self.hdc.shell("ps -ef | grep uitest | grep singleness").output.strip()
            lines = result.splitlines()
            for line in lines:
                if 'uitest start-daemon singleness' in line:
                    parts = line.split()
                    pid = parts[1]
                    self.hdc.shell(f"kill -9 {pid}")
                    logger.debug(f"Killed uitest process with PID {pid}")

            self.hdc.shell("uitest start-daemon singleness")
            time.sleep(.5)

        except subprocess.CalledProcessError as e:
            logger.error(f"An error occurred: {e}")
