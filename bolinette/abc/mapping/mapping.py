from abc import ABC, abstractmethod
from typing import Any

from bolinette import abc


class Mapper(ABC):
    @abstractmethod
    def payload(self, model_name: str, key: str): ...

    @abstractmethod
    def response(self, model_name: str, key: str): ...

    @abstractmethod
    def register(self, model: abc.core.Model): ...

    @abstractmethod
    def marshall(self, definition, entity, *, skip_none=False, as_list=False, use_foreign_key=False): ...
