# -*- coding: utf-8 -*-

import socket
import json
import time
import os
import typing
import subprocess
import atexit
import hashlib
import threading
import numpy as np
from queue import Queue
from datetime import datetime

import cv2

from . import logger
from .driver import Driver
from .exception import ScreenRecordError


# Developing


class _ScreenRecord:
    def __init__(self, driver: Driver):
        self._client = driver._client
        self.video_path = None

        self.jpeg_queue = Queue()
        self.threads: typing.List[threading.Thread] = []
        self.stop_event = threading.Event()

    def _send_message(self, api: str, args: list):
        _msg = {
            "module": "com.ohos.devicetest.hypiumApiHelper",
            "method": "Captures",
            "params": {
                "api": api,
                "args": args
            },
            "request_id": datetime.now().strftime("%Y%m%d%H%M%S%f")
        }
        self._client._send_msg(_msg)

    def start(self, video_path: str):

        self.video_path = video_path

        self._send_message("startCaptureScreen", [])

        reply: str = self._client._recv_msg(1024, decode=True)
        if "true" in reply:
            record_th = threading.Thread(target=self._record_worker)
            writer_th = threading.Thread(target=self._video_writer)
            record_th.start()
            writer_th.start()
            self.threads.extend([record_th, writer_th])
        else:
            raise ScreenRecordError("Failed to start device screen capture.")

    def _record_worker(self):
        """Capture screen frames and save current frames."""

        # JPEG start and end markers.
        start_flag = b'\xff\xd8'
        end_flag = b'\xff\xd9'
        buffer = bytearray()
        while not self.stop_event.is_set():
            try:
                buffer += self._client._recv_msg(4096 * 1024)
            except Exception as e:
                print(f"Error receiving data: {e}")
                break

            start_idx = buffer.find(start_flag)
            end_idx = buffer.find(end_flag)
            while start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                # Extract one JPEG image
                jpeg_image: bytearray = buffer[start_idx:end_idx + 2]
                self.jpeg_queue.put(jpeg_image)

                buffer = buffer[end_idx + 2:]

                # Search for the next JPEG image in the buffer
                start_idx = buffer.find(start_flag)
                end_idx = buffer.find(end_flag)

    def _video_writer(self):
        """Write frames to video file."""
        cv2_instance = None
        while not self.stop_event.is_set():
            if not self.jpeg_queue.empty():
                jpeg_image = self.jpeg_queue.get(timeout=0.1)
                img = cv2.imdecode(np.frombuffer(jpeg_image, np.uint8), cv2.IMREAD_COLOR)
                if cv2_instance is None:
                    height, width = img.shape[:2]
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    cv2_instance = cv2.VideoWriter(self.video_path, fourcc, 10, (width, height))

                cv2_instance.write(img)

        if cv2_instance:
            cv2_instance.release()

    def stop(self) -> str:
        try:
            self.stop_event.set()
            for t in self.threads:
                t.join()

            self._send_message("stopCaptureScreen", [])
            self._client._recv_msg(1024, decode=True)
        except Exception as e:
            logger.error(f"An error occurred: {e}")

        return self.video_path
