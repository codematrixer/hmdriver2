# -*- coding: utf-8 -*-
import re
import socket
import json
import time
import os
import glob
import typing
import subprocess
from datetime import datetime
from functools import cached_property

from . import logger
from .hdc import HdcWrapper
from .proto import HypiumResponse, DriverData
from .exception import InvokeHypiumError, InvokeCaptures


UITEST_SERVICE_PORT = 8012
SOCKET_TIMEOUT = 20
ASSETS_PATH = os.path.join(os.path.dirname(__file__), "assets")
AGENT_CLEAR_PATH = ["app", "commons-", "agent", "libagent_antry"]


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

        file_postfix = ".so"
        device_agent_path = "/data/local/tmp/agent.so"
        arch_info = self.hdc.shell("file /system/bin/uitest").output.strip()
        if "x86_64" in arch_info:
            file_postfix = ".x86_64_so"
        local_path = ""
        local_ver = "0.0.0"
        for agent_file in glob.glob(os.path.join(ASSETS_PATH, "uitest_agent*so")):
            file_name = os.path.split(agent_file)[1]
            if not agent_file.endswith(file_postfix):
                continue
            matcher = re.search(r'\d{1,3}[.]\d{1,3}[.]\d{1,3}', file_name)
            if not matcher:
                continue
            ver = matcher.group()[0]
            if ver.split('.') > local_ver.split('.'):
                local_ver, local_path = ver, agent_file
        device_ver_info = self.hdc.shell(f"cat {device_agent_path} | grep -a UITEST_AGENT_LIBRARY").output.strip()
        matcher = re.search(r'\d{1,3}[.]\d{1,3}[.]\d{1,3}', device_ver_info)
        device_ver = matcher.group(0) if matcher else "0.0.0"
        logger.debug(f"local agent version {local_ver}, device agent version {device_ver}")
        if device_ver.split('.') < local_ver.split('.'):
            logger.debug(f"start update agent, path is {local_path}")
            self._kill_uitest_service()
            for file in AGENT_CLEAR_PATH:
                self.hdc.shell(f"rm /data/local/tmp/{file}*")
            self.hdc.send_file(local_path, device_agent_path)
            self.hdc.shell(f"chmod +x {device_agent_path}")
            logger.debug("Update agent finish.")
        else:
            logger.debug("Device agent is up to date!")

    def get_devicetest_proc_pid(self):
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
        for pid in self.get_devicetest_proc_pid():
            self.hdc.shell(f"kill -9 {pid}")
            logger.debug(f"Killed uitest process with PID {pid}")

    def _restart_uitest_service(self):
        """
        Restart the UITest daemon.

        Note: 'hdc shell aa test' will also start a uitest daemon.
        $ hdc shell ps -ef |grep uitest
        shell        44306     1 25 11:03:37 ?    00:00:16 uitest start-daemon singleness
        shell        44416     1 2 11:03:42 ?     00:00:01 uitest start-daemon com.hmtest.uitest@4x9@1"
        """
        try:
            self._kill_uitest_service()
            self.hdc.shell("uitest start-daemon singleness")
            time.sleep(.5)

        except subprocess.CalledProcessError as e:
            logger.error(f"An error occurred: {e}")
