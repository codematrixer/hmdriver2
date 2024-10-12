# -*- coding: utf-8 -*-

import os
import time
import pytest

from hmdriver2.driver import Driver
from hmdriver2.proto import KeyCode, DisplayRotation


@pytest.fixture
def d():
    d = Driver("FMR0223C13000649")
    yield d
    d._client.release()


def test_driver(d):
    dd = Driver("FMR0223C13000649")
    assert id(dd) == id(d)


def test_device_info(d):
    info = d.device_info
    assert info.sdkVersion == "12"
    assert info.cpuAbi == "arm64-v8a"
    assert info.displaySize == (1260, 2720)


def test_force_start_app(d):
    d.unlock()
    d.force_start_app("com.samples.test.uitest", "EntryAbility")


def test_clear_app(d):
    d.clear_app("com.samples.test.uitest")


def test_install_app(d):
    pass


def test_uninstall_app(d):
    pass


def test_list_apps(d):
    assert "com.samples.test.uitest" in d.list_apps()


def test_has_app(d):
    assert d.has_app("com.samples.test.uitest")


def test_current_app(d):
    d.force_start_app("com.samples.test.uitest", "EntryAbility")
    assert d.current_app() == ("com.samples.test.uitest", "EntryAbility")


def test_get_app_info(d):
    assert d.get_app_info("com.samples.test.uitest")


def test_go_back(d):
    d.go_back()


def test_go_home(d):
    d.go_home()


def test_press_key(d):
    d.press_key(KeyCode.POWER)


def test_screen_on(d):
    d.screen_on()
    assert d.hdc.screen_state() == "AWAKE"


def test_screen_off(d):
    d.screen_off()
    time.sleep(3)
    assert d.hdc.screen_state() != "AWAKE"


def test_unlock(d):
    d.screen_off()
    d.unlock()
    d.force_start_app("com.samples.test.uitest", "EntryAbility")
    assert d.hdc.screen_state() == "AWAKE"


def test_display_size(d):
    w, h = d.display_size
    assert w, h == (1260, 2720)


def test_display_rotation(d):
    assert d.display_rotation == DisplayRotation.ROTATION_0


def test_open_url(d):
    d.open_url("http://www.baidu.com")


def test_pull_file(d):
    rpath = "/data/local/tmp/agent.so"
    lpath = "./agent.so"
    d.pull_file(rpath, lpath)
    assert os.path.exists(lpath)


def test_push_file(d):
    lpath = "~/arch.png"
    rpath = "/data/local/tmp/arch.png"
    d.push_file(lpath, rpath)


def test_screenshot(d) -> str:
    lpath = "./test.png"
    d.screenshot(lpath)
    assert os.path.exists(lpath)


def test_shell(d):
    d.shell("pwd")


def test_click(d):
    d.click(500, 1000)
    d.click(0.5, 0.4)
    d.click(0.5, 400)


def test_double_click(d):
    d.double_click(500, 1000)
    d.double_click(0.5, 0.4)
    d.double_click(0.5, 400)


def test_long_click(d):
    d.long_click(500, 1000)
    d.long_click(0.5, 0.4)
    d.long_click(0.5, 400)


def test_swipe(d):
    d.swipe(0.5, 0.8, 0.5, 0.4, speed=2000)


def test_input_text(d):
    d.input_text("adbcdfg")


def test_dump_hierarchy(d):
    data = d.dump_hierarchy()
    print(data)
    assert data


def test_toast(d):
    d.force_start_app("com.samples.test.uitest", "EntryAbility")
    d.toast_watcher.start()
    d(type="Button", text="showToast").click()
    toast = d.toast_watcher.get_toast()
    print(f"toast: {toast}")
    assert toast == "testMessage"


def test_gesture(d):
    d(id="drag").click()
    d.gesture.start(630, 984, interval=1).move(0.2, 0.4, interval=.5).pause(interval=1).move(0.5, 0.6, interval=.5).pause(interval=1).action()
    d.go_back()


def test_gesture_click(d):
    d.gesture.start(0.77, 0.49).action()


def test_screenrecord(d):
    path = "test.mp4"
    d.screenrecord.start(path)

    d.force_start_app("com.samples.test.uitest", "EntryAbility")
    time.sleep(5)
    for _ in range(3):
        d.swipe(0.5, 0.8, 0.5, 0.3)
    d.go_home()

    path = d.screenrecord.stop()
    assert os.path.isfile(path)


def test_screenrecord2(d):
    path = "test2.mp4"
    with d.screenrecord.start(path):
        d.force_start_app("com.samples.test.uitest", "EntryAbility")
        time.sleep(5)
        for _ in range(3):
            d.swipe(0.5, 0.8, 0.5, 0.3)
    d.go_home()

    assert os.path.isfile(path)


def test_xpath(d):
    d.force_start_app("com.samples.test.uitest", "EntryAbility")

    xpath1 = '//root[1]/Row[1]/Column[1]/Row[1]/Button[3]'   # showToast
    xpath2 = '//*[@text="showDialog"]'

    d.toast_watcher.start()
    d.xpath(xpath1).click()
    toast = d.toast_watcher.get_toast()
    print(f"toast: {toast}")
    assert toast == "testMessage"

    d.xpath(xpath2).click()