from typing import Callable, TypeVar

from bolinette.core import Cache, __user_cache__, meta


class Controller:
    pass


class ControllerMeta:
    def __init__(self, path: str) -> None:
        self.path = path


TCtrl = TypeVar("TCtrl", bound=Controller)


def controller(path: str, /, *, cache: Cache | None = None) -> Callable[[type[TCtrl]], type[TCtrl]]:
    def decorator(cls: type[TCtrl]) -> type[TCtrl]:
        meta.set(cls, ControllerMeta(path))
        (cache or __user_cache__).add(ControllerMeta, cls)
        return cls

    return decorator
