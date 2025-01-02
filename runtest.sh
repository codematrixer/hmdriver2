#!/bin/bash

pytest tests --capture=no
# pytest tests/test_driver.py::test_toast --capture=no
# pytest tests/test_driver.py::test_toast tests/test_driver.py::test_get_app_main_ability --capture=no
