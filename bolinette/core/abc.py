from abc import ABC as _ABC
from typing import TypeVar as _TypeVar

from bolinette import core


T_Instance = _TypeVar("T_Instance")


class WithContext(_ABC):
    def __init__(self, context: "core.BolinetteContext", **kwargs):
        self.__blnt_ctx__ = context

    @property
    def context(self):
        return self.__blnt_ctx__
