# -*- coding: utf-8 -*-

import typing
import threading
import numpy as np
from queue import Queue
from datetime import datetime

import cv2

from . import logger
from ._client import HmClient
from .driver import Driver
from .exception import ScreenRecordError


class RecordClient(HmClient):
    def __init__(self, serial: str, driver: Driver):
        super().__init__(serial)
        self.driver = driver

        self.video_path = None
        self.jpeg_queue = Queue()
        self.threads: typing.List[threading.Thread] = []
        self.stop_event = threading.Event()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def _send_msg(self, api: str, args: list):
        _msg = {
            "module": "com.ohos.devicetest.hypiumApiHelper",
            "method": "Captures",
            "params": {
                "api": api,
                "args": args
            },
            "request_id": datetime.now().strftime("%Y%m%d%H%M%S%f")
        }
        super()._send_msg(_msg)

    def start(self, video_path: str):
        logger.info("Start RecordClient connection")

        self._connect_sock()

        self.video_path = video_path

        self._send_msg("startCaptureScreen", [])

        reply: str = self._recv_msg(1024, decode=True, print=False)
        if "true" in reply:
            record_th = threading.Thread(target=self._record_worker)
            writer_th = threading.Thread(target=self._video_writer)
            record_th.daemon = True
            writer_th.daemon = True
            record_th.start()
            writer_th.start()
            self.threads.extend([record_th, writer_th])
        else:
            raise ScreenRecordError("Failed to start device screen capture.")

        return self

    def _record_worker(self):
        """Capture screen frames and save current frames."""

        # JPEG start and end markers.
        start_flag = b'\xff\xd8'
        end_flag = b'\xff\xd9'
        buffer = bytearray()
        while not self.stop_event.is_set():
            try:
                buffer += self._recv_msg(4096 * 1024, decode=False, print=False)
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

            self._send_msg("stopCaptureScreen", [])
            self._recv_msg(1024, decode=True, print=False)

            self.release()

            # Invalidate the cached property
            self.driver._invalidate_cache('screenrecord')

        except Exception as e:
            logger.error(f"An error occurred: {e}")

        return self.video_path
