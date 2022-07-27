import inspect
from collections.abc import Callable
from typing import Any, TypeVar

from bolinette.core import Cache, Injection, InjectionStrategy, __core_cache__
from bolinette.core.exceptions import InitError

T = TypeVar("T")


class Environment:
    def __init__(self, cache: Cache, inject: Injection) -> None:
        self._cache = cache
        self._inject = inject
        for name, cls in self._cache.env_sections:
            if len(inspect.signature(cls).parameters) != 0:
                raise InitError(
                    f"Environment section {cls} must have an empty __init__ method"
                )
            self._inject.add(cls, InjectionStrategy.Singleton)

    @staticmethod
    def _init_section(cls: type[Any]):
        pass


def environment(
    name: str, *, cache: Cache | None = None
) -> Callable[[type[T]], type[T]]:
    def decorator(cls: type[T]) -> type[T]:
        if not inspect.isclass(cls):
            raise InitError(
                f"{cls} must be a class to be decorated with @{environment.__name__}"
            )
        (cache or __core_cache__).add_env_section(name, cls)
        return cls

    return decorator


class Url:
    path: str


@environment("core")
class CoreSection:
    debug: bool
    print: int = 3
    strings: list[str]
    urls: list[Url]
