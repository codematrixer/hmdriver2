# -*- coding: utf-8 -*-

class ElementNotFoundError(Exception):
    pass


class ElementFoundTimeout(Exception):
    pass


class HmDriverError(Exception):
    pass


class DeviceNotFoundError(Exception):
    pass


class HdcError(Exception):
    pass


class InvokeHypiumError(Exception):
    pass


class InvokeCaptures(Exception):
    pass


class InjectGestureError(Exception):
    pass


class ScreenRecordError(Exception):
    pass
