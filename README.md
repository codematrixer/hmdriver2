# hmdriver2

>在写这个项目前github上已有个[hmdirver](https://github.com/mrx1203/hmdriver)框架，但它是侵入式的（需要提前在手机端安装一个testRunner app）。另外鸿蒙官方提供的`hypium`自动化框架，使用复杂，依赖繁杂。于是决定重新写一套框架，解决上述两个框架的弊端。

`hmdriver2`是一款支持`鸿蒙Next`系统的UI自动化框架，**无侵入式**，提供应用管理，UI操作，元素定位等功能，轻量高效，上手简单，为你快速实现鸿蒙应用的自动化测试需求。


# Feature
- 支持鸿蒙Next系统的所有设备自动化
- **无侵入式**，无需在手机安装基于arkTS的testRunner APP
- 支持应用管理（启动/停止/安装/卸载/获取应用列表等等）
- 支持UI操作和元素定位（点击/滑动/输入/元素查找等等等）
- 稳定高效，直接和鸿蒙底层uitest服务通过socket通信
- 使用python语言编写测试用例，上手简单，即插即用

# Install
```
pip3 install hmdirver2
```

# Usage

```python
from hmdriver2.driver import Driver
from hmdriver2.proto import KeyCode, DisplayRotation, ComponentData


# New driver
d = Driver("FMR0223C13000649")

# App management
d.start_app("com.kuaishou.hmapp", "EntryAbility")
d.stop_app("com.kuaishou.hmapp")
d.clear_app("com.kuaishou.hmapp")
d.install_app("~/develop/harmony_prj/demo.hap")

# KeyCode: https://docs.openharmony.cn/pages/v4.1/en/application-dev/reference/apis-input-kit/js-apis-keycode.md
d.go_back()
d.go_home()
d.press_key(KeyCode.POWER)
d.screen_on()
d.screen_off()
d.unlock()

# Device Info
# DeviceInfo(productName='HUAWEI Mate 60 Pro', model='ALN-AL00', sdkVersion='12', sysVersion='ALN-AL00 5.0.0.60(SP12DEVC00E61R4P9log)', cpuAbi='arm64-v8a', wlanIp='172.31.125.111', displaySize=(1260, 2720), displayRotation=<DisplayRotation.ROTATION_0: 0>)
d.device_info
d.display_size
d.display_rotation

# Execute HDC shell command
d.shell("ls -l")

# Open scheme
d.open_url("http://www.baidu.com")

# Push and pull files
d.pull_file(rpath, lpath)
d.push_file(lpath, rpath)

# Device Screenshot
d.screenshot(lpath)

# Device touch
d.click(500, 1000)
d.click(0.5, 0.4)
d.double_click(500, 1000)
d.double_click(0.5, 0.4)
d.long_click(500, 1000)
d.long_click(0.5, 0.4)
d.swipe(0.5, 0.8, 0.5, 0.4, speed=2000)
d.input_text(0.5, 0.5, "adbcdfg")

# App Element
d(text="showToast").info
# {
#     "id": "",
#     "key": "",
#     "type": "Button",
#     "text": "showToast",
#     "description": "",
#     "isSelected": False,
#     "isChecked": False,
#     "isEnabled": True,
#     "isFocused": False,
#     "isCheckable": False,
#     "isClickable": True,
#     "isLongClickable": False,
#     "isScrollable": False,
#     "bounds": {
#         "left": 539,
#         "top": 1282,
#         "right": 832,
#         "bottom": 1412
#     },
#     "boundsCenter": {
#         "x": 685,
#         "y": 1347
#     }
# }

d(id="swiper").exists()
d(type="Button", text="showToast").exists()
d(text="showToast", isAfter=True).exists()
d(text="showToast").click_if_exists()
d(type="Button", index=3).click()
d(text="showToast").double_click()
d(text="showToast").long_click()

component: ComponentData = d(type="ListItem", index=1).find_component()
d(type="ListItem").drag_to(component)

d(text="showToast").input_text("abc")
d(text="showToast").clear_text()
d(text="showToast").pinch_in()
d(text="showToast").pinch_out()


```




# Refer to

- https://developer.huawei.com/consumer/cn/doc/harmonyos-guides-V5/ut-V5
- https://github.com/mrx1203/hmdriver