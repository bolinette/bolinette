from collections.abc import Callable
from typing import ClassVar, Protocol

from escondite import Cache

from bolinette.core import meta


class Controller(Protocol):
    pass


class ControllerMeta:
    KEY: ClassVar[str] = "__blnt_web_controller_meta__"

    def __init__(self, path: str) -> None:
        self.path = path


def controller[CtrlT: Controller](
    path: str,
    /,
    *,
    cache: Cache | None = None,
) -> Callable[[type[CtrlT]], type[CtrlT]]:
    def decorator(cls: type[CtrlT]) -> type[CtrlT]:
        meta.set(cls, ControllerMeta.KEY, ControllerMeta(path))
        Cache.with_fallback(cache).add(ControllerMeta.KEY, cls)
        return cls

    return decorator
