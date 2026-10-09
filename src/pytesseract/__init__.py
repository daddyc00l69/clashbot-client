# -*- coding: utf-8 -*-
"""ClashBot AI - Resilient pytesseract stub & delegator.
Satisfies client-side GUI initialization while all combat vision and OCR
execute on the Cloud Server.
"""
from __future__ import annotations

import sys


class Output:
    BYTES = "bytes"
    DATAFRAME = "dataframe"
    DICT = "dict"
    STRING = "string"


class TesseractError(Exception):
    pass


class TesseractNotFoundError(TesseractError):
    pass


class ALTONotSupported(TesseractError):
    pass


class TSVNotSupported(TesseractError):
    pass


class _Pytesseract:
    tesseract_cmd = "tesseract"


pytesseract = _Pytesseract()
tesseract_cmd = "tesseract"


def image_to_string(image, *args, **kwargs) -> str:
    return ""


def image_to_data(image, *args, **kwargs) -> str:
    return ""


def image_to_boxes(image, *args, **kwargs) -> str:
    return ""


def image_to_osd(image, *args, **kwargs) -> str:
    return ""


def image_to_pdf_or_hocr(image, *args, **kwargs) -> bytes:
    return b""


def image_to_alto_xml(image, *args, **kwargs) -> str:
    return ""


def get_tesseract_version() -> str:
    return "5.0.0"


def get_languages(*args, **kwargs) -> list[str]:
    return ["eng"]


def run_and_get_output(*args, **kwargs) -> str:
    return ""


def run_and_get_multiple_output(*args, **kwargs) -> list[str]:
    return []


__all__ = [
    "image_to_string",
    "image_to_data",
    "image_to_boxes",
    "image_to_osd",
    "image_to_pdf_or_hocr",
    "image_to_alto_xml",
    "get_tesseract_version",
    "get_languages",
    "run_and_get_output",
    "run_and_get_multiple_output",
    "Output",
    "TesseractError",
    "TesseractNotFoundError",
    "ALTONotSupported",
    "TSVNotSupported",
    "pytesseract",
    "tesseract_cmd",
]
