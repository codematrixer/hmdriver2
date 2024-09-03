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


def test_driver(d):
    dd = Driver("FMR0223C13000649")
    assert id(dd) == id(d)


def test_force_start_app(d):
    d.force_start_app("com.kuaishou.hmapp", "EntryAbility")


def test_clear_app(d):
    d.clear_app("com.kuaishou.hmapp")


def test_install_app(d):
    pass


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
    d.force_start_app("com.kuaishou.hmapp", "EntryAbility")
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
    lpath = "~/hilog.log1"
    rpath = "/data/local/tmp/hilog.log"
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
    d.input_text(0.5, 0.5, "adbcdfg")