# -*- coding: utf-8 -*-

import json
from enum import Enum
from typing import Union, List, Tuple
from dataclasses import dataclass, asdict


@dataclass
class CommandResult:
    output: str
    error: str
    exit_code: int


class DisplayRotation(int, Enum):
    ROTATION_0 = 0
    ROTATION_90 = 1
    ROTATION_180 = 2
    ROTATION_270 = 3

    @classmethod
    def from_value(cls, value):
        for rotation in cls:
            if rotation.value == value:
                return rotation
        raise ValueError(f"No matching DisplayRotation for value: {value}")


class AppState:
    INIT = 0        # 初始化状态，应用正在初始化
    READY = 1       # 就绪状态，应用已初始化完毕
    FOREGROUND = 2  # 前台状态，应用位于前台
    FOCUS = 3       # 获焦状态。（预留状态，当前暂不支持）
    BACKGROUND = 4  # 后台状态，应用位于后台
    EXIT = 5        # 退出状态，应用已退出


@dataclass
class DeviceInfo:
    productName: str
    model: str
    sdkVersion: str
    sysVersion: str
    cpuAbi: str
    wlanIp: str
    displaySize: tuple
    displayRotation: DisplayRotation


@dataclass
class HypiumResponse:
    """
    Example:
    {"result":"On#1"}
    {"result":null}
    {"result":null,"exception":"Can not connect to AAMS, RET_ERR_CONNECTION_EXIST"}
    {"exception":{"code":401,"message":"(PreProcessing: APiCallInfoChecker)Illegal argument count"}}
    """
    result: Union[List, bool, str, None] = None
    exception: Union[List, bool, str, None] = None


@dataclass
class ByData:
    value: str  # "On#0"


@dataclass
class DriverData:
    value: str   # "Driver#0"


@dataclass
class ComponentData:
    value: str  # "Component#0"


@dataclass
class Rect:
    left: int
    right: int
    top: int
    bottom: int

    def get_center(self) -> Tuple[int, int]:
        return int((self.left + self.right) / 2), int((self.top + self.bottom) / 2)


@dataclass
class Point:
    x: int
    y: int

    def to_tuple(self):
        return self.x, self.y

    def to_dict(self):
        return {
            "x": self.x,
            "y": self.y
        }


@dataclass
class ElementInfo:
    id: str
    key: str
    type: str
    text: str
    description: str
    isSelected: bool
    isChecked: bool
    isEnabled: bool
    isFocused: bool
    isCheckable: bool
    isClickable: bool
    isLongClickable: bool
    isScrollable: bool
    bounds: Rect
    boundsCenter: Point

    def __str__(self) -> str:
        return json.dumps(asdict(self), indent=4)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=4)

    def to_dict(self) -> dict:
        return asdict(self)


class KeyCode(Enum):
    """
    Openharmony键盘码
    """
    FN = 0  # 功能（Fn）键
    UNKNOWN = -1  # 未知按键
    HOME = 1  # 功能（Home）键
    BACK = 2  # 返回键
    MEDIA_PLAY_PAUSE = 10  # 多媒体键播放/暂停
    MEDIA_STOP = 11  # 多媒体键停止
    MEDIA_NEXT = 12  # 多媒体键下一首
    MEDIA_PREVIOUS = 13  # 多媒体键上一首
    MEDIA_REWIND = 14  # 多媒体键快退
    MEDIA_FAST_FORWARD = 15  # 多媒体键快进
    VOLUME_UP = 16  # 音量增加键
    VOLUME_DOWN = 17  # 音量减小键
    POWER = 18  # 电源键
    CAMERA = 19  # 拍照键
    VOLUME_MUTE = 22  # 扬声器静音键
    MUTE = 23  # 话筒静音键
    BRIGHTNESS_UP = 40  # 亮度调节按键调亮
    BRIGHTNESS_DOWN = 41  # 亮度调节按键调暗
    NUM_0 = 2000  # 按键’0’
    NUM_1 = 2001  # 按键’1’
    NUM_2 = 2002  # 按键’2’
    NUM_3 = 2003  # 按键’3’
    NUM_4 = 2004  # 按键’4’
    NUM_5 = 2005  # 按键’5’
    NUM_6 = 2006  # 按键’6’
    NUM_7 = 2007  # 按键’7’
    NUM_8 = 2008  # 按键’8’
    NUM_9 = 2009  # 按键’9’
    STAR = 2010  # 按键’*’
    POUND = 2011  # 按键’#’
    DPAD_UP = 2012  # 导航键向上
    DPAD_DOWN = 2013  # 导航键向下
    DPAD_LEFT = 2014  # 导航键向左
    DPAD_RIGHT = 2015  # 导航键向右
    DPAD_CENTER = 2016  # 导航键确定键
    A = 2017  # 按键’A’
    B = 2018  # 按键’B’
    C = 2019  # 按键’C’
    D = 2020  # 按键’D’
    E = 2021  # 按键’E’
    F = 2022  # 按键’F’
    G = 2023  # 按键’G’
    H = 2024  # 按键’H’
    I = 2025  # 按键’I’
    J = 2026  # 按键’J’
    K = 2027  # 按键’K’
    L = 2028  # 按键’L’
    M = 2029  # 按键’M’
    N = 2030  # 按键’N’
    O = 2031  # 按键’O’
    P = 2032  # 按键’P’
    Q = 2033  # 按键’Q’
    R = 2034  # 按键’R’
    S = 2035  # 按键’S’
    T = 2036  # 按键’T’
    U = 2037  # 按键’U’
    V = 2038  # 按键’V’
    W = 2039  # 按键’W’
    X = 2040  # 按键’X’
    Y = 2041  # 按键’Y’
    Z = 2042  # 按键’Z’
    COMMA = 2043  # 按键’,’
    PERIOD = 2044  # 按键’.’
    ALT_LEFT = 2045  # 左Alt键
    ALT_RIGHT = 2046  # 右Alt键
    SHIFT_LEFT = 2047  # 左Shift键
    SHIFT_RIGHT = 2048  # 右Shift键
    TAB = 2049  # Tab键
    SPACE = 2050  # 空格键
    SYM = 2051  # 符号修改器按键
    EXPLORER = 2052  # 浏览器功能键，此键用于启动浏览器应用程序。
    ENVELOPE = 2053  # 电子邮件功能键，此键用于启动电子邮件应用程序。
    ENTER = 2054  # 回车键
    DEL = 2055  # 退格键
    GRAVE = 2056  # 按键’`’
    MINUS = 2057  # 按键’-’
    EQUALS = 2058  # 按键’=’
    LEFT_BRACKET = 2059  # 按键’[’
    RIGHT_BRACKET = 2060  # 按键’]’
    BACKSLASH = 2061  # 按键’\’
    SEMICOLON = 2062  # 按键’;’
    APOSTROPHE = 2063  # 按键’‘’(单引号)
    SLASH = 2064  # 按键’/’
    AT = 2065  # 按键’@’
    PLUS = 2066  # 按键’+’
    MENU = 2067  # 菜单键
    PAGE_UP = 2068  # 向上翻页键
    PAGE_DOWN = 2069  # 向下翻页键
    ESCAPE = 2070  # ESC键
    FORWARD_DEL = 2071  # 删除键
    CTRL_LEFT = 2072  # 左Ctrl键
    CTRL_RIGHT = 2073  # 右Ctrl键
    CAPS_LOCK = 2074  # 大写锁定键
    SCROLL_LOCK = 2075  # 滚动锁定键
    META_LEFT = 2076  # 左元修改器键
    META_RIGHT = 2077  # 右元修改器键
    FUNCTION = 2078  # 功能键
    SYSRQ = 2079  # 系统请求/打印屏幕键
    BREAK = 2080  # Break/Pause键
    MOVE_HOME = 2081  # 光标移动到开始键
    MOVE_END = 2082  # 光标移动到末尾键
    INSERT = 2083  # 插入键
    FORWARD = 2084  # 前进键
    MEDIA_PLAY = 2085  # 多媒体键播放
    MEDIA_PAUSE = 2086  # 多媒体键暂停
    MEDIA_CLOSE = 2087  # 多媒体键关闭
    MEDIA_EJECT = 2088  # 多媒体键弹出
    MEDIA_RECORD = 2089  # 多媒体键录音
    F1 = 2090  # 按键’F1’
    F2 = 2091  # 按键’F2’
    F3 = 2092  # 按键’F3’
    F4 = 2093  # 按键’F4’
    F5 = 2094  # 按键’F5’
    F6 = 2095  # 按键’F6’
    F7 = 2096  # 按键’F7’
    F8 = 2097  # 按键’F8’
    F9 = 2098  # 按键’F9’
    F10 = 2099  # 按键’F10’
    F11 = 2100  # 按键’F11’
    F12 = 2101  # 按键’F12’
    NUM_LOCK = 2102  # 小键盘锁
    NUMPAD_0 = 2103  # 小键盘按键’0’
    NUMPAD_1 = 2104  # 小键盘按键’1’
    NUMPAD_2 = 2105  # 小键盘按键’2’
    NUMPAD_3 = 2106  # 小键盘按键’3’
    NUMPAD_4 = 2107  # 小键盘按键’4’
    NUMPAD_5 = 2108  # 小键盘按键’5’
    NUMPAD_6 = 2109  # 小键盘按键’6’
    NUMPAD_7 = 2110  # 小键盘按键’7’
    NUMPAD_8 = 2111  # 小键盘按键’8’
    NUMPAD_9 = 2112  # 小键盘按键’9’
    NUMPAD_DIVIDE = 2113  # 小键盘按键’/’
    NUMPAD_MULTIPLY = 2114  # 小键盘按键’*’
    NUMPAD_SUBTRACT = 2115  # 小键盘按键’-’
    NUMPAD_ADD = 2116  # 小键盘按键’+’
    NUMPAD_DOT = 2117  # 小键盘按键’.’
    NUMPAD_COMMA = 2118  # 小键盘按键’,’
    NUMPAD_ENTER = 2119  # 小键盘按键回车
    NUMPAD_EQUALS = 2120  # 小键盘按键’=’
    NUMPAD_LEFT_PAREN = 2121  # 小键盘按键’(’
    NUMPAD_RIGHT_PAREN = 2122  # 小键盘按键’)’
    VIRTUAL_MULTITASK = 2210  # 虚拟多任务键
    SLEEP = 2600  # 睡眠键
    ZENKAKU_HANKAKU = 2601  # 日文全宽/半宽键
    ND = 2602  # 102nd按键
    RO = 2603  # 日文Ro键
    KATAKANA = 2604  # 日文片假名键
    HIRAGANA = 2605  # 日文平假名键
    HENKAN = 2606  # 日文转换键
    KATAKANA_HIRAGANA = 2607  # 日语片假名/平假名键
    MUHENKAN = 2608  # 日文非转换键
    LINEFEED = 2609  # 换行键
    MACRO = 2610  # 宏键
    NUMPAD_PLUSMINUS = 2611  # 数字键盘上的加号/减号键
    SCALE = 2612  # 扩展键
    HANGUEL = 2613  # 日文韩语键
    HANJA = 2614  # 日文汉语键
    YEN = 2615  # 日元键
    STOP = 2616  # 停止键
    AGAIN = 2617  # 重复键
    PROPS = 2618  # 道具键
    UNDO = 2619  # 撤消键
    COPY = 2620  # 复制键
    OPEN = 2621  # 打开键
    PASTE = 2622  # 粘贴键
    FIND = 2623  # 查找键
    CUT = 2624  # 剪切键
    HELP = 2625  # 帮助键
    CALC = 2626  # 计算器特殊功能键，用于启动计算器应用程序
    FILE = 2627  # 文件按键
    BOOKMARKS = 2628  # 书签键
    NEXT = 2629  # 下一个按键
    PLAYPAUSE = 2630  # 播放/暂停键
    PREVIOUS = 2631  # 上一个按键
    STOPCD = 2632  # CD停止键
    CONFIG = 2634  # 配置键
    REFRESH = 2635  # 刷新键
    EXIT = 2636  # 退出键
    EDIT = 2637  # 编辑键
    SCROLLUP = 2638  # 向上滚动键
    SCROLLDOWN = 2639  # 向下滚动键
    NEW = 2640  # 新建键
    REDO = 2641  # 恢复键
    CLOSE = 2642  # 关闭键
    PLAY = 2643  # 播放键
    BASSBOOST = 2644  # 低音增强键
    PRINT = 2645  # 打印键
    CHAT = 2646  # 聊天键
    FINANCE = 2647  # 金融键
    CANCEL = 2648  # 取消键
    KBDILLUM_TOGGLE = 2649  # 键盘灯光切换键
    KBDILLUM_DOWN = 2650  # 键盘灯光调亮键
    KBDILLUM_UP = 2651  # 键盘灯光调暗键
    SEND = 2652  # 发送键
    REPLY = 2653  # 答复键
    FORWARDMAIL = 2654  # 邮件转发键
    SAVE = 2655  # 保存键
    DOCUMENTS = 2656  # 文件键
    VIDEO_NEXT = 2657  # 下一个视频键
    VIDEO_PREV = 2658  # 上一个视频键
    BRIGHTNESS_CYCLE = 2659  # 背光渐变键
    BRIGHTNESS_ZERO = 2660  # 亮度调节为0键
    DISPLAY_OFF = 2661  # 显示关闭键
    BTN_MISC = 2662  # 游戏手柄上的各种按键
    GOTO = 2663  # 进入键
    INFO = 2664  # 信息查看键
    PROGRAM = 2665  # 程序键
    PVR = 2666  # 个人录像机(PVR)键
    SUBTITLE = 2667  # 字幕键
    FULL_SCREEN = 2668  # 全屏键
    KEYBOARD = 2669  # 键盘
    ASPECT_RATIO = 2670  # 屏幕纵横比调节键
    PC = 2671  # 端口控制键
    TV = 2672  # TV键
    TV2 = 2673  # TV键2
    VCR = 2674  # 录像机开启键
    VCR2 = 2675  # 录像机开启键2
    SAT = 2676  # SIM卡应用工具包（SAT）键
    CD = 2677  # CD键
    TAPE = 2678  # 磁带键
    TUNER = 2679  # 调谐器键
    PLAYER = 2680  # 播放器键
    DVD = 2681  # DVD键
    AUDIO = 2682  # 音频键
    VIDEO = 2683  # 视频键
    MEMO = 2684  # 备忘录键
    CALENDAR = 2685  # 日历键
    RED = 2686  # 红色指示器
    GREEN = 2687  # 绿色指示器
    YELLOW = 2688  # 黄色指示器
    BLUE = 2689  # 蓝色指示器
    CHANNELUP = 2690  # 频道向上键
    CHANNELDOWN = 2691  # 频道向下键
    LAST = 2692  # 末尾键
    RESTART = 2693  # 重启键
    SLOW = 2694  # 慢速键
    SHUFFLE = 2695  # 随机播放键
    VIDEOPHONE = 2696  # 可视电话键
    GAMES = 2697  # 游戏键
    ZOOMIN = 2698  # 放大键
    ZOOMOUT = 2699  # 缩小键
    ZOOMRESET = 2700  # 缩放重置键
    WORDPROCESSOR = 2701  # 文字处理键
    EDITOR = 2702  # 编辑器键
    SPREADSHEET = 2703  # 电子表格键
    GRAPHICSEDITOR = 2704  # 图形编辑器键
    PRESENTATION = 2705  # 演示文稿键
    DATABASE = 2706  # 数据库键标
    NEWS = 2707  # 新闻键
    VOICEMAIL = 2708  # 语音信箱
    ADDRESSBOOK = 2709  # 通讯簿
    MESSENGER = 2710  # 通信键
    BRIGHTNESS_TOGGLE = 2711  # 亮度切换键
    SPELLCHECK = 2712  # AL拼写检查
    COFFEE = 2713  # 终端锁/屏幕保护程序
    MEDIA_REPEAT = 2714  # 媒体循环键
    IMAGES = 2715  # 图像键
    BUTTONCONFIG = 2716  # 按键配置键
    TASKMANAGER = 2717  # 任务管理器
    JOURNAL = 2718  # 日志按键
    CONTROLPANEL = 2719  # 控制面板键
    APPSELECT = 2720  # 应用程序选择键
    SCREENSAVER = 2721  # 屏幕保护程序键
    ASSISTANT = 2722  # 辅助键
    KBD_LAYOUT_NEXT = 2723  # 下一个键盘布局键
    BRIGHTNESS_MIN = 2724  # 最小亮度键
    BRIGHTNESS_MAX = 2725  # 最大亮度键
    KBDINPUTASSIST_PREV = 2726  # 键盘输入Assist_Previous
    KBDINPUTASSIST_NEXT = 2727  # 键盘输入Assist_Next
    KBDINPUTASSIST_PREVGROUP = 2728  # 键盘输入Assist_Previous
    KBDINPUTASSIST_NEXTGROUP = 2729  # 键盘输入Assist_Next
    KBDINPUTASSIST_ACCEPT = 2730  # 键盘输入Assist_Accept
    KBDINPUTASSIST_CANCEL = 2731  # 键盘输入Assist_Cancel
    FRONT = 2800  # 挡风玻璃除雾器开关
    SETUP = 2801  # 设置键
    WAKE_UP = 2802  # 唤醒键
    SENDFILE = 2803  # 发送文件按键
    DELETEFILE = 2804  # 删除文件按键
    XFER = 2805  # 文件传输(XFER)按键
    PROG1 = 2806  # 程序键1
    PROG2 = 2807  # 程序键2
    MSDOS = 2808  # MS-DOS键（微软磁盘操作系统
    SCREENLOCK = 2809  # 屏幕锁定键
    DIRECTION_ROTATE_DISPLAY = 2810  # 方向旋转显示键
    CYCLEWINDOWS = 2811  # Windows循环键
    COMPUTER = 2812  # 按键
    EJECTCLOSECD = 2813  # 弹出CD键
    ISO = 2814  # ISO键
    MOVE = 2815  # 移动键
    F13 = 2816  # 按键’F13’
    F14 = 2817  # 按键’F14’
    F15 = 2818  # 按键’F15’
    F16 = 2819  # 按键’F16’
    F17 = 2820  # 按键’F17’
    F18 = 2821  # 按键’F18’
    F19 = 2822  # 按键’F19’
    F20 = 2823  # 按键’F20’
    F21 = 2824  # 按键’F21’
    F22 = 2825  # 按键’F22’
    F23 = 2826  # 按键’F23’
    F24 = 2827  # 按键’F24’
    PROG3 = 2828  # 程序键3
    PROG4 = 2829  # 程序键4
    DASHBOARD = 2830  # 仪表板
    SUSPEND = 2831  # 挂起键
    HP = 2832  # 高阶路径键
    SOUND = 2833  # 音量键
    QUESTION = 2834  # 疑问按键
    CONNECT = 2836  # 连接键
    SPORT = 2837  # 运动按键
    SHOP = 2838  # 商城键
    ALTERASE = 2839  # 交替键
    SWITCHVIDEOMODE = 2841  # 在可用视频之间循环输出（监视器/LCD/TV输出/等）
    BATTERY = 2842  # 电池按键
    BLUETOOTH = 2843  # 蓝牙按键
    WLAN = 2844  # 无线局域网
    UWB = 2845  # 超宽带（UWB）
    WWAN_WIMAX = 2846  # WWANWiMAX按键
    RFKILL = 2847  # 控制所有收音机的键
    CHANNEL = 3001  # 向上频道键
    BTN_0 = 3100  # 按键0
    BTN_1 = 3101  # 按键1
    BTN_2 = 3102  # 按键2
    BTN_3 = 3103  # 按键3
    BTN_4 = 3104  # 按键4
    BTN_5 = 3105  # 按键5
    BTN_6 = 3106  # 按键6
    BTN_7 = 3107  # 按键7
    BTN_8 = 3108  # 按键8
    BTN_9 = 3109  # 按键9