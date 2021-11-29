from abc import ABC, abstractmethod
from typing import Any


class Environment(ABC):
    @abstractmethod
    def __getitem__(self, key: str) -> Any: ...

    @abstractmethod
    def __contains__(self, key: str) -> bool:...

    @abstractmethod
    def __setitem__(self, key: str, value) -> None: ...

    @abstractmethod
    def get(self, key: str, default=None) -> Any: ...

    @abstractmethod
    def get_all(self, *, startswith: str = None) -> dict[str, Any]: ...
