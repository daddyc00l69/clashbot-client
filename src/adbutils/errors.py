# -*- coding: utf-8 -*-
class AdbError(Exception): pass
class AdbTimeout(Exception): pass
class AdbConnectionError(Exception): pass

def __getattr__(name):
    if name.startswith("__") and name.endswith("__"):
        raise AttributeError(name)
    return type(name, (Exception,), {})
