# -*- coding: utf-8 -*-
"""
ClashBot AI - Client Stub Package for adbutils
"""

class Network:
    TCP = "tcp"
    UNIX = "unix"

class AdbDevice:
    def __init__(self, *args, **kwargs):
        pass
    def shell(self, *args, **kwargs):
        return ""
    def screencap(self, *args, **kwargs):
        return None
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return lambda *args, **kwargs: None

class AdbClient:
    def __init__(self, *args, **kwargs):
        pass
    def device(self, *args, **kwargs):
        return AdbDevice()
    def device_list(self, *args, **kwargs):
        return []
    def iter_device(self, *args, **kwargs):
        return []
    def connect(self, *args, **kwargs):
        return None
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return lambda *args, **kwargs: None

adb = AdbClient()

class ScreenrecordExtension:
    pass

class InstallExtension:
    pass

class AdbError(Exception):
    pass

class AdbTimeout(Exception):
    pass

def __getattr__(name):
    if name.startswith("__") and name.endswith("__"):
        raise AttributeError(name)
    return lambda *args, **kwargs: None
