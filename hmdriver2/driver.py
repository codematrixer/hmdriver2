# -*- coding: utf-8 -*-

import json
import uuid
from functools import cached_property  # python3.8+
from typing import Type, Tuple, Dict, Union, List, Optional, Any

from . import logger
from ._client import HmClient
from ._uiobject import UiObject
from .exception import DeviceNotFoundError
from .hdc import list_devices
from .proto import HypiumResponse, KeyCode, Point, DisplayRotation, DeviceInfo, CommandResult
from .utils import delay


class Driver:
    """
    Harmony OS 设备驱动类
    
    提供设备控制、应用管理、UI 操作等功能的主要接口。
    采用单例模式，每个设备序列号对应一个实例。
    """

    # 单例存储字典
    _instance: Dict[str, "Driver"] = {}

    def __new__(cls: Type["Driver"], serial: Optional[str] = None) -> "Driver":
        """
        确保每个设备序列号只创建一个 Driver 实例
        
        如果 serial 为 None，使用 list_devices() 的第一个设备
        
        Args:
            serial: 设备序列号，为 None 时使用第一个可用设备
            
        Returns:
            Driver: 对应序列号的 Driver 实例
        """
        serial = cls._prepare_serial(serial)

        if serial not in cls._instance:
            instance = super().__new__(cls)
            cls._instance[serial] = instance
            # 临时存储序列号用于初始化
            instance._serial_for_init = serial
        return cls._instance[serial]

    def __init__(self, serial: Optional[str] = None):
        """
        初始化 Driver 实例
        
        只有在实例未初始化时才执行初始化
        
        Args:
            serial: 设备序列号，为 None 时使用第一个可用设备
            
        Raises:
            ValueError: 初始化时缺少序列号
        """
        if hasattr(self, "_initialized") and self._initialized:
            return

        # 使用在 __new__ 中准备的序列号
        serial = getattr(self, "_serial_for_init", serial)
        if serial is None:
            raise ValueError("初始化时需要设备序列号")

        self.serial = serial
        self._client = HmClient(self.serial)
        self.hdc = self._client.hdc
        self._init_hmclient()
        self._initialized = True  # 标记实例已初始化
        del self._serial_for_init  # 清理临时属性

    @classmethod
    def _prepare_serial(cls, serial: Optional[str] = None) -> str:
        """
        准备设备序列号
        
        如果未提供序列号，使用第一个可用设备
        
        Args:
            serial: 设备序列号，为 None 时使用第一个可用设备
            
        Returns:
            str: 准备好的设备序列号
            
        Raises:
            DeviceNotFoundError: 未找到设备或指定的设备不存在
        """
        devices = list_devices()
        if not devices:
            raise DeviceNotFoundError("未找到设备，请连接设备")

        if serial is None:
            logger.info(f"未提供序列号，使用第一个设备: {devices[0]}")
            return devices[0]
        if serial not in devices:
            raise DeviceNotFoundError(f"未找到设备 [{serial}]")
        return serial

    def __call__(self, **kwargs) -> UiObject:
        """
        将 Driver 实例作为函数调用，返回 UiObject 实例
        
        Args:
            **kwargs: 传递给 UiObject 构造函数的参数
            
        Returns:
            UiObject: 创建的 UiObject 实例
        """
        return UiObject(self._client, **kwargs)

    def __del__(self):
        """
        析构函数，清理资源
        """
        Driver._instance.clear()
        if hasattr(self, '_client') and self._client:
            self._client.release()

    def _init_hmclient(self):
        """初始化 HmClient 连接"""
        self._client.start()

    def _invoke(self, api: str, args: Optional[List[Any]] = None) -> HypiumResponse:
        """
        调用 Hypium API
        
        Args:
            api: API 名称
            args: API 参数列表，默认为空列表
            
        Returns:
            HypiumResponse: API 调用响应
        """
        if args is None:
            args = []
        return self._client.invoke(api, this="Driver#0", args=args)

    @delay
    def start_app(self, package_name: str, page_name: Optional[str] = None):
        """
        启动应用
        
        如果未提供 page_name，将通过 get_app_main_ability 获取主 Ability
        
        Args:
            package_name: 应用包名
            page_name: Ability 名称，默认为 None
        """
        if not page_name:
            page_name = self.get_app_main_ability(package_name).get('name', 'MainAbility')
        self.hdc.start_app(package_name, page_name)

    def force_start_app(self, package_name: str, page_name: Optional[str] = None):
        """
        强制启动应用
        
        先返回主屏幕，停止应用，然后启动应用
        
        Args:
            package_name: 应用包名
            page_name: Ability 名称，默认为 None
        """
        self.go_home()
        self.stop_app(package_name)
        self.start_app(package_name, page_name)

    def stop_app(self, package_name: str):
        """
        停止应用
        
        Args:
            package_name: 应用包名
        """
        self.hdc.stop_app(package_name)

    def clear_app(self, package_name: str):
        """
        清除应用缓存和数据
        
        Args:
            package_name: 应用包名
        """
        self.hdc.shell(f"bm clean -n {package_name} -c")  # 清除缓存
        self.hdc.shell(f"bm clean -n {package_name} -d")  # 清除数据

    def install_app(self, apk_path: str):
        """
        安装应用
        
        Args:
            apk_path: 应用安装包路径
        """
        self.hdc.install(apk_path)

    def uninstall_app(self, package_name: str):
        """
        卸载应用
        
        Args:
            package_name: 应用包名
        """
        self.hdc.uninstall(package_name)

    def list_apps(self) -> List:
        """
        列出设备上的应用
        
        Returns:
            List: 应用列表
        """
        return self.hdc.list_apps()

    def has_app(self, package_name: str) -> bool:
        """
        检查设备上是否安装了指定应用
        
        Args:
            package_name: 应用包名
            
        Returns:
            bool: 应用存在返回 True，否则返回 False
        """
        return self.hdc.has_app(package_name)

    def current_app(self) -> Tuple[str, str]:
        """
        获取当前前台应用信息
        
        Returns:
            Tuple[str, str]: 包含应用包名和页面名称的元组
                             如果未找到前台应用，返回 (None, None)
        """
        return self.hdc.current_app()

    def get_app_info(self, package_name: str) -> Dict:
        """
        获取应用详细信息
        
        Args:
            package_name: 应用包名
            
        Returns:
            Dict: 包含应用信息的字典，解析错误时返回空字典
        """
        app_info = {}
        data: CommandResult = self.hdc.shell(f"bm dump -n {package_name}")
        output = data.output
        try:
            json_start = output.find("{")
            json_end = output.rfind("}") + 1
            json_output = output[json_start:json_end]

            app_info = json.loads(json_output)
        except Exception as e:
            logger.error(f"解析应用信息时出错: {e}")
        return app_info

    def get_app_abilities(self, package_name: str) -> List[Dict]:
        """
        获取应用的 Abilities
        
        Args:
            package_name: 应用包名
            
        Returns:
            List[Dict]: 包含应用 Abilities 信息的字典列表
        """
        result = []
        app_info = self.get_app_info(package_name)
        hap_module_infos = app_info.get("hapModuleInfos", [])
        main_entry = app_info.get("mainEntry")
        for hap_module_info in hap_module_infos:
            # 尝试读取 moduleInfo
            try:
                ability_infos = hap_module_info.get("abilityInfos", [])
                module_main = hap_module_info.get("mainAbility", "")
            except Exception as e:
                logger.warning(f"解析 moduleInfo 失败: {repr(e)}")
                continue
            # 尝试读取 abilityInfo
            for ability_info in ability_infos:
                try:
                    is_launcher_ability = False
                    skills = ability_info.get('skills', [])
                    if skills and "action.system.home" in skills[0].get("actions", []):
                        is_launcher_ability = True
                    icon_ability_info = {
                        "name": ability_info.get("name", ""),
                        "moduleName": ability_info.get("moduleName", ""),
                        "moduleMainAbility": module_main,
                        "mainModule": main_entry,
                        "isLauncherAbility": is_launcher_ability
                    }
                    result.append(icon_ability_info)
                except Exception as e:
                    logger.warning(f"解析 ability_info 失败: {repr(e)}")
                    continue
        logger.debug(f"所有 abilities: {result}")
        return result

    def get_app_main_ability(self, package_name: str) -> Dict:
        """
        获取应用的主 Ability
        
        Args:
            package_name: 应用包名
            
        Returns:
            Dict: 包含应用主 Ability 信息的字典，未找到时返回空字典
        """
        abilities = self.get_app_abilities(package_name)
        if not abilities:
            return {}
        for item in abilities:
            score = 0
            name = item.get("name", "")
            if name and name == item.get("moduleMainAbility", ""):
                score += 1
            module_name = item.get("moduleName", "")
            if module_name and module_name == item.get("mainModule", ""):
                score += 1
            item["score"] = score
        abilities.sort(key=lambda x: (not x.get("isLauncherAbility", False), -x.get("score", 0)))
        logger.debug(f"主 ability: {abilities[0]}")
        return abilities[0]

    @cached_property
    def toast_watcher(self):
        """
        获取 Toast 监视器
        
        Returns:
            _Watcher: Toast 监视器实例
        """
        obj = self

        class _Watcher:
            """Toast 监视器内部类"""

            def start(self) -> bool:
                """
                开始监视 Toast
                
                Returns:
                    bool: 成功返回 True
                """
                api = "Driver.uiEventObserverOnce"
                resp: HypiumResponse = obj._invoke(api, args=["toastShow"])
                return resp.result

            def get_toast(self, timeout: int = 3) -> Optional[str]:
                """
                获取 Toast 内容
                
                Args:
                    timeout: 超时时间（秒），默认为 3
                    
                Returns:
                    Optional[str]: Toast 内容，未捕获到返回 None
                """
                api = "Driver.getRecentUiEvent"
                resp: HypiumResponse = obj._invoke(api, args=[timeout])
                if resp.result:
                    return resp.result.get("text")
                return None

        return _Watcher()

    @delay
    def go_back(self):
        """按返回键"""
        self.hdc.send_key(KeyCode.BACK)

    @delay
    def go_home(self):
        """按主页键"""
        self.hdc.send_key(KeyCode.HOME)

    @delay
    def go_recent(self):
        """打开最近任务"""
        self.press_keys(KeyCode.META_LEFT, KeyCode.TAB)

    @delay
    def press_key(self, key_code: Union[KeyCode, int]):
        """
        按下单个按键
        
        Args:
            key_code: 按键代码，可以是 KeyCode 枚举或整数
        """
        self.hdc.send_key(key_code)

    @delay
    def press_keys(self, key_code1: Union[KeyCode, int], key_code2: Union[KeyCode, int]):
        """
        按下组合键
        
        Args:
            key_code1: 第一个按键代码
            key_code2: 第二个按键代码
        """
        code1 = key_code1.value if isinstance(key_code1, KeyCode) else key_code1
        code2 = key_code2.value if isinstance(key_code2, KeyCode) else key_code2

        api = "Driver.triggerCombineKeys"
        self._invoke(api, args=[code1, code2])

    def screen_on(self):
        """唤醒屏幕"""
        self.hdc.wakeup()

    def screen_off(self):
        """关闭屏幕"""
        self.hdc.wakeup()
        self.press_key(KeyCode.POWER)

    @delay
    def unlock(self):
        """
        解锁屏幕
        
        先唤醒屏幕，然后从屏幕底部向上滑动
        """
        self.screen_on()
        w, h = self.display_size
        self.swipe(0.5 * w, 0.8 * h, 0.5 * w, 0.2 * h, speed=6000)

    @cached_property
    def display_size(self) -> Tuple[int, int]:
        """
        获取屏幕尺寸
        
        Returns:
            Tuple[int, int]: 屏幕宽度和高度
        """
        api = "Driver.getDisplaySize"
        resp: HypiumResponse = self._invoke(api)
        w, h = resp.result.get("x"), resp.result.get("y")
        return w, h

    @cached_property
    def display_rotation(self) -> DisplayRotation:
        """
        获取屏幕旋转状态
        
        Returns:
            DisplayRotation: 屏幕旋转状态枚举值
        """
        api = "Driver.getDisplayRotation"
        value = self._invoke(api).result
        return DisplayRotation.from_value(value)

    def set_display_rotation(self, rotation: DisplayRotation):
        """
        设置屏幕旋转状态
        
        Args:
            rotation: 屏幕旋转状态枚举值
        """
        api = "Driver.setDisplayRotation"
        self._invoke(api, args=[rotation.value])

    @cached_property
    def device_info(self) -> DeviceInfo:
        """
        获取设备详细信息
        
        Returns:
            DeviceInfo: 包含设备各种属性的对象
        """
        hdc = self.hdc
        return DeviceInfo(
            productName=hdc.product_name(),
            model=hdc.model(),
            sdkVersion=hdc.sdk_version(),
            sysVersion=hdc.sys_version(),
            cpuAbi=hdc.cpu_abi(),
            wlanIp=hdc.wlan_ip(),
            displaySize=self.display_size,
            displayRotation=self.display_rotation
        )

    @delay
    def open_url(self, url: str, system_browser: bool = True):
        """
        打开 URL
        
        Args:
            url: 要打开的 URL
            system_browser: 是否使用系统浏览器，默认为 True
        """
        if system_browser:
            # 使用系统浏览器
            self.hdc.shell(f"aa start -A ohos.want.action.viewData -e entity.system.browsable -U {url}")
        else:
            # 默认方法
            self.hdc.shell(f"aa start -U {url}")

    def pull_file(self, rpath: str, lpath: str):
        """
        从设备拉取文件到本地
        
        Args:
            rpath: 设备上的文件路径
            lpath: 本地保存路径
        """
        self.hdc.recv_file(rpath, lpath)

    def push_file(self, lpath: str, rpath: str):
        """
        推送本地文件到设备
        
        Args:
            lpath: 本地文件路径
            rpath: 设备上的保存路径
        """
        self.hdc.send_file(lpath, rpath)

    def screenshot(self, path: str) -> str:
        """
        截取设备屏幕
        
        Args:
            path: 本地保存路径
            
        Returns:
            str: 截图保存路径
        """
        _uuid = uuid.uuid4().hex
        _tmp_path = f"/data/local/tmp/_tmp_{_uuid}.jpeg"
        self.shell(f"snapshot_display -f {_tmp_path}")
        self.pull_file(_tmp_path, path)
        self.shell(f"rm -rf {_tmp_path}")  # 删除临时文件
        return path

    def shell(self, cmd) -> CommandResult:
        """
        执行 Shell 命令
        
        Args:
            cmd: 要执行的命令
            
        Returns:
            CommandResult: 命令执行结果
        """
        return self.hdc.shell(cmd)

    def _to_abs_pos(self, x: Union[int, float], y: Union[int, float]) -> Point:
        """
        将百分比坐标转换为绝对屏幕坐标
        
        Args:
            x: X 坐标，可以是百分比（0-1）或绝对值
            y: Y 坐标，可以是百分比（0-1）或绝对值
            
        Returns:
            Point: 包含绝对屏幕坐标的 Point 对象
            
        Raises:
            AssertionError: 坐标为负数时抛出
        """
        assert x >= 0, "X 坐标不能为负数"
        assert y >= 0, "Y 坐标不能为负数"

        # 只有在需要时才获取显示尺寸
        if x < 1 or y < 1:
            w, h = self.display_size
            
            if x < 1:
                x = w * x
            if y < 1:
                y = h * y
                
        # 只进行一次整数转换
        return Point(int(x), int(y))

    @delay
    def click(self, x: Union[int, float], y: Union[int, float]):
        """
        点击屏幕
        
        Args:
            x: X 坐标，可以是百分比（0-1）或绝对值
            y: Y 坐标，可以是百分比（0-1）或绝对值
        """
        # self.hdc.tap(point.x, point.y)
        point = self._to_abs_pos(x, y)
        api = "Driver.click"
        self._invoke(api, args=[point.x, point.y])

    @delay
    def double_click(self, x: Union[int, float], y: Union[int, float]):
        """
        双击屏幕
        
        Args:
            x: X 坐标，可以是百分比（0-1）或绝对值
            y: Y 坐标，可以是百分比（0-1）或绝对值
        """
        point = self._to_abs_pos(x, y)
        api = "Driver.doubleClick"
        self._invoke(api, args=[point.x, point.y])

    @delay
    def long_click(self, x: Union[int, float], y: Union[int, float]):
        """
        长按屏幕
        
        Args:
            x: X 坐标，可以是百分比（0-1）或绝对值
            y: Y 坐标，可以是百分比（0-1）或绝对值
        """
        point = self._to_abs_pos(x, y)
        api = "Driver.longClick"
        self._invoke(api, args=[point.x, point.y])

    @delay
    def swipe(self, x1: Union[int, float], y1: Union[int, float],
              x2: Union[int, float], y2: Union[int, float], speed: int = 2000):
        """
        在屏幕上滑动
        
        Args:
            x1: 起始 X 坐标，可以是百分比（0-1）或绝对值
            y1: 起始 Y 坐标，可以是百分比（0-1）或绝对值
            x2: 结束 X 坐标，可以是百分比（0-1）或绝对值
            y2: 结束 Y 坐标，可以是百分比（0-1）或绝对值
            speed: 滑动速度（像素/秒），默认为 2000，范围：200-40000
                  如果超出范围，将设为默认值 2000
        """
        point1 = self._to_abs_pos(x1, y1)
        point2 = self._to_abs_pos(x2, y2)

        if speed < 200 or speed > 40000:
            logger.warning("`speed` 不在范围 [200-40000] 内，设置为默认值 2000")
            speed = 2000

        api = "Driver.swipe"
        self._invoke(api, args=[point1.x, point1.y, point2.x, point2.y, speed])

    @cached_property
    def swipe_ext(self):
        """
        获取扩展滑动功能
        
        用法示例:
        d.swipe_ext("up")
        d.swipe_ext("up", box=(0.2, 0.2, 0.8, 0.8))
        
        Returns:
            SwipeExt: 扩展滑动功能实例
        """
        from ._swipe import SwipeExt
        return SwipeExt(self)

    @delay
    def input_text(self, text: str):
        """
        在当前焦点输入框中输入文本
        
        注意：调用此方法前，输入框必须已获得焦点
        
        Args:
            text: 要输入的文本
            
        Returns:
            HypiumResponse: API 调用响应
        """
        return self._invoke("Driver.inputText", args=[{"x": 1, "y": 1}, text])

    def dump_hierarchy(self) -> str:
        """
        导出界面层次结构
        
        Returns:
            str: 界面层次结构的 JSON 字符串
        """
        result = self._client.invoke_captures("captureLayout").result
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False)

    @cached_property
    def gesture(self):
        """
        获取手势操作功能
        
        Returns:
            _Gesture: 手势操作功能实例
        """
        from ._gesture import _Gesture
        return _Gesture(self)

    @cached_property
    def screenrecord(self):
        """
        获取屏幕录制功能
        
        Returns:
            RecordClient: 屏幕录制功能实例
        """
        from ._screenrecord import RecordClient
        return RecordClient(self.serial, self)

    def _invalidate_cache(self, attribute_name: str):
        """
        使缓存的属性失效
        
        Args:
            attribute_name: 要使失效的属性名
        """
        if attribute_name in self.__dict__:
            del self.__dict__[attribute_name]

    @cached_property
    def xpath(self):
        """
        获取 XPath 查询功能
        
        用法示例:
        d.xpath("//*[@text='Hello']").click()
        
        Returns:
            _XPath: XPath 查询功能实例
        """
        from ._xpath import _XPath
        return _XPath(self)
