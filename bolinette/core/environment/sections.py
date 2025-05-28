from collections.abc import Callable

from bolinette.core import Cache, __user_cache__, meta


class EnvSectionMeta:
    def __init__(self, name: str) -> None:
        self.name = name


def environment[EnvT](
    name: str,
    *,
    cache: Cache | None = None,
) -> Callable[[type[EnvT]], type[EnvT]]:
    def decorator(cls: type[EnvT]) -> type[EnvT]:
        meta.set(cls, EnvSectionMeta(name))
        (cache or __user_cache__).add(EnvSectionMeta, cls)
        return cls

    return decorator
