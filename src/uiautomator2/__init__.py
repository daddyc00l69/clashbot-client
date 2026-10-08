# -*- coding: utf-8 -*-
"""ClashBot AI - Client Stub for uiautomator2"""
class Device:
    def __init__(self, *args, **kwargs): pass
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"): raise AttributeError(name)
        return lambda *args, **kwargs: None

def connect(*args, **kwargs): return Device()
def __getattr__(name):
    if name.startswith("__") and name.endswith("__"): raise AttributeError(name)
    return lambda *args, **kwargs: None
