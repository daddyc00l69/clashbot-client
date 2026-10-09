# -*- coding: utf-8 -*-
"""
ClashBot AI - Client Stub: Vision Engine
All OpenCV template matching, digit OCR reading, and computer vision
execute exclusively on the ClashBot Cloud Server.
"""

class VisionMeta(type):
    def __getattr__(cls, name):
        def _dummy(*args, **kwargs):
            if name.startswith("is_"):
                return False
            if name.startswith("read_loot"):
                return (0, 0, 0)
            return None
        return _dummy

class Vision(metaclass=VisionMeta):
    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        def _dummy(*args, **kwargs):
            if name.startswith("is_"):
                return False
            if name.startswith("read_loot"):
                return (0, 0, 0)
            return None
        return _dummy

    @classmethod
    def read_loot(cls, *args, **kwargs):
        return (0, 0, 0)

    @classmethod
    def match_template(cls, *args, **kwargs):
        return None

GLOBAL_VISION = Vision()

__all__ = ["Vision", "GLOBAL_VISION"]

def __getattr__(name):
    return getattr(GLOBAL_VISION, name, None)
