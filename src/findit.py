# -*- coding: utf-8 -*-
"""ClashBot AI - Client Stub for findit"""
class FindIt:
    def __init__(self, *args, **kwargs): pass
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"): raise AttributeError(name)
        return lambda *args, **kwargs: None

def __getattr__(name):
    if name.startswith("__") and name.endswith("__"): raise AttributeError(name)
    return lambda *args, **kwargs: None
