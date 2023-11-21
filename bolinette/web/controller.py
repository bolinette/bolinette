from collections.abc import Callable
from typing import Protocol

from bolinette.core import Cache, __user_cache__, meta


class Controller(Protocol):
    pass


class ControllerMeta:
    def __init__(self, path: str) -> None:
        self.path = path


def controller[TCtrl: Controller](
    path: str,
    /,
    *,
    cache: Cache | None = None,
) -> Callable[[type[TCtrl]], type[TCtrl]]:
    def decorator(cls: type[TCtrl]) -> type[TCtrl]:
        meta.set(cls, ControllerMeta(path))
        (cache or __user_cache__).add(ControllerMeta, cls)
        return cls

    return decorator
