from collections.abc import Callable
from typing import Any

from escondite import Cache

STARTUP_CACHE_KEY = "__blnt_core_startup__"


def startup[**P, T](*, cache: Cache | None = None) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        Cache.with_fallback(cache).add(STARTUP_CACHE_KEY, func)
        return func

    return decorator


def get_startup_functions(cache: Cache) -> set[Callable[..., Any]]:
    return cache.get(STARTUP_CACHE_KEY, raises=False)
