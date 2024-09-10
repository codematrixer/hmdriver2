# -*- coding: utf-8 -*-

from hmdriver2.driver import Driver
from hmdriver2.proto import DeviceInfo, KeyCode, ComponentData


# New driver
d = Driver("FMR0223C13000649")

# Device Info
info: DeviceInfo = d.device_info
# DeviceInfo(productName='HUAWEI Mate 60 Pro', model='ALN-AL00', sdkVersion='12', sysVersion='ALN-AL00 5.0.0.60(SP12DEVC00E61R4P9log)', cpuAbi='arm64-v8a', wlanIp='172.31.125.111', displaySize=(1260, 2720), displayRotation=<DisplayRotation.ROTATION_0: 0>)

print(d.display_size)
print(d.display_rotation)

d.install_app("~/develop/harmony_prj/demo.hap")
d.clear_app("com.samples.test.uitest")
d.force_start_app("com.samples.test.uitest", "EntryAbility")
d.get_app_info("com.samples.test.uitest")

# KeyCode: https://github.com/codematrixer/hmdriver2/blob/master/hmdriver2/proto.py
d.go_back()
d.go_home()
d.press_key(KeyCode.POWER)
d.screen_on()
d.screen_off()
d.unlock()

# Execute HDC shell command
d.shell("ls -l")

# Open scheme
d.open_url("http://www.baidu.com")

# Push and pull files
rpath = "/data/local/tmp/agent.so"
lpath = "./agent.so"
d.pull_file("", lpath)
d.push_file(lpath, rpath)

# Device Screenshot
d.screenshot("./test.png")

# Device touch
d.click(500, 1000)
d.click(0.5, 0.4)  # "If of type float, it represents percentage coordinates."
d.double_click(500, 1000)
d.double_click(0.5, 0.4)
d.long_click(500, 1000)
d.long_click(0.5, 0.4)
d.swipe(0.5, 0.8, 0.5, 0.4, speed=2000)
d.input_text(0.5, 0.5, "adbcdfg")

# Device touch gersture
d.gesture.start(630, 984, interval=.5).move(0.2, 0.4, interval=.5).pause(interval=1).move(0.5, 0.6, interval=.5).pause(interval=1).action()
d.go_back()
d.gesture.start(0.77, 0.49).action()


# Toast Watcher
d.toast_watcher.start()
# do somethings 比如触发toast
toast = d.toast_watcher.get_toast()
print(toast)

# Dump hierarchy
d.dump_hierarchy()


# App Element
d(id="swiper").exists()
d(type="Button", text="tab_recrod").exists()
d(text="tab_recrod", isAfter=True).exists()
d(text="tab_recrod").click_if_exists()
d(type="Button", index=3).click()
d(text="tab_recrod").double_click()
d(text="tab_recrod").long_click()

component: ComponentData = d(type="ListItem", index=1).find_component()
d(type="ListItem").drag_to(component)

d(text="tab_recrod").input_text("abc")
d(text="tab_recrod").clear_text()
d(text="tab_recrod").pinch_in()
d(text="tab_recrod").pinch_out()

d(text="tab_recrod").info
"""
{
    "id": "",
    "key": "",
    "type": "Button",
    "text": "tab_recrod",
    "description": "",
    "isSelected": False,
    "isChecked": False,
    "isEnabled": True,
    "isFocused": False,
    "isCheckable": False,
    "isClickable": True,
    "isLongClickable": False,
    "isScrollable": False,
    "bounds": {
        "left": 539,
        "top": 1282,
        "right": 832,
        "bottom": 1412
    },
    "boundsCenter": {
        "x": 685,
        "y": 1347
    }
}
"""
