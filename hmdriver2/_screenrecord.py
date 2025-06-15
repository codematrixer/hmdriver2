# -*- coding: utf-8 -*-

import queue
import threading
from datetime import datetime
from typing import List, Optional, Any

import cv2
import numpy as np

from . import logger
from ._client import HmClient
from .driver import Driver
from .exception import ScreenRecordError

# 常量定义
JPEG_START_FLAG = b'\xff\xd8'  # JPEG 图像开始标记
JPEG_END_FLAG = b'\xff\xd9'    # JPEG 图像结束标记
VIDEO_FPS = 10                 # 视频帧率
VIDEO_CODEC = 'mp4v'           # 视频编码格式
QUEUE_TIMEOUT = 0.1            # 队列超时时间（秒）


class RecordClient(HmClient):
    """
    屏幕录制客户端
    
    继承自 HmClient，提供设备屏幕录制功能
    """
    
    def __init__(self, serial: str, d: Driver):
        """
        初始化屏幕录制客户端
        
        Args:
            serial: 设备序列号
            d: Driver 实例
        """
        super().__init__(serial)
        self.d = d

        self.video_path: Optional[str] = None
        self.jpeg_queue: queue.Queue = queue.Queue()
        self.threads: List[threading.Thread] = []
        self.stop_event: threading.Event = threading.Event()

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出时停止录制"""
        self.stop()

    def _send_msg(self, api: str, args: Optional[List[Any]] = None):
        """
        发送消息到设备
        
        重写父类方法，使用 Captures API
        
        Args:
            api: API 名称
            args: API 参数列表，默认为空列表
        """
        if args is None:
            args = []
            
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
        """
        开始屏幕录制
        
        Args:
            video_path: 视频保存路径
            
        Returns:
            RecordClient: 当前实例，支持链式调用
            
        Raises:
            ScreenRecordError: 启动屏幕录制失败时抛出
        """
        logger.info("开始屏幕录制")

        # 连接设备
        self._connect_sock()

        self.video_path = video_path

        # 发送开始录制命令
        self._send_msg("startCaptureScreen", [])

        # 检查响应
        reply: str = self._recv_msg(decode=True, print=False)
        if "true" in reply:
            # 创建并启动工作线程
            record_th = threading.Thread(target=self._record_worker)
            writer_th = threading.Thread(target=self._video_writer)
            record_th.daemon = True
            writer_th.daemon = True
            record_th.start()
            writer_th.start()
            self.threads.extend([record_th, writer_th])
        else:
            raise ScreenRecordError("启动设备屏幕录制失败")

        return self

    def _record_worker(self):
        """
        屏幕帧捕获工作线程
        
        捕获屏幕帧并保存当前帧
        """
        buffer = bytearray()
        while not self.stop_event.is_set():
            try:
                buffer += self._recv_msg(decode=False, print=False)
            except Exception as e:
                logger.error(f"接收数据时出错: {e}")
                break

            # 查找 JPEG 图像的开始和结束标记
            start_idx = buffer.find(JPEG_START_FLAG)
            end_idx = buffer.find(JPEG_END_FLAG)
            
            # 处理所有完整的 JPEG 图像
            while start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                # 提取一个 JPEG 图像
                jpeg_image: bytearray = buffer[start_idx:end_idx + 2]
                self.jpeg_queue.put(jpeg_image)

                # 从缓冲区中移除已处理的数据
                buffer = buffer[end_idx + 2:]

                # 在缓冲区中查找下一个 JPEG 图像
                start_idx = buffer.find(JPEG_START_FLAG)
                end_idx = buffer.find(JPEG_END_FLAG)

    def _video_writer(self):
        """
        视频写入工作线程
        
        将帧写入视频文件
        """
        cv2_instance = None
        img = None
        while not self.stop_event.is_set():
            try:
                # 从队列获取 JPEG 图像
                jpeg_image = self.jpeg_queue.get(timeout=QUEUE_TIMEOUT)
                img = cv2.imdecode(np.frombuffer(jpeg_image, np.uint8), cv2.IMREAD_COLOR)
            except queue.Empty:
                pass
                
            # 跳过无效图像
            if img is None or img.size == 0:
                continue
                
            # 首次获取有效图像时初始化视频写入器
            if cv2_instance is None:
                height, width = img.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*VIDEO_CODEC)
                cv2_instance = cv2.VideoWriter(self.video_path, fourcc, VIDEO_FPS, (width, height))

            # 写入帧
            cv2_instance.write(img)

        # 释放资源
        if cv2_instance:
            cv2_instance.release()

    def stop(self) -> str:
        """
        停止屏幕录制
        
        Returns:
            str: 视频保存路径
        """
        try:
            # 设置停止事件，通知工作线程退出
            self.stop_event.set()
            
            # 等待所有工作线程结束
            for t in self.threads:
                t.join()

            # 发送停止录制命令
            self._send_msg("stopCaptureScreen", [])
            self._recv_msg(decode=True, print=False)

            # 释放资源
            self.release()

            # 使缓存的属性失效
            self.d._invalidate_cache('screenrecord')

        except Exception as e:
            logger.error(f"停止屏幕录制时出错: {e}")

        return self.video_path
