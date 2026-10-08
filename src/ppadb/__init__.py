# -*- coding: utf-8 -*-
"""ClashBot AI - Client Stub for pure-python-adb (ppadb)"""
class Client:
    def __init__(self, *args, **kwargs): pass
    def devices(self, *args, **kwargs): return []
    def device(self, *args, **kwargs): return None
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"): raise AttributeError(name)
        return lambda *args, **kwargs: None

def __getattr__(name):
    if name.startswith("__") and name.endswith("__"): raise AttributeError(name)
    return lambda *args, **kwargs: None
