from collections.abc import Callable
from typing import Protocol

from bolinette.core import Cache, __user_cache__, meta


class EnvSectionMeta:
    def __init__(self, name: str) -> None:
        self.name = name


class EnvironmentSection(Protocol):
    def __init__(self) -> None:
        pass


def environment[EnvT: EnvironmentSection](
    name: str,
    *,
    cache: Cache | None = None,
) -> Callable[[type[EnvT]], type[EnvT]]:
    def decorator(cls: type[EnvT]) -> type[EnvT]:
        meta.set(cls, EnvSectionMeta(name))
        (cache or __user_cache__).add(EnvironmentSection, cls)
        return cls

    return decorator


class CoreSection:
    debug: bool = False
