from collections.abc import Callable

from bolinette.core import Cache, __user_cache__

STARTUP_CACHE_KEY = object()


def startup[**P, T](*, cache: Cache | None = None) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        (cache or __user_cache__).add(STARTUP_CACHE_KEY, func)
        return func

    return decorator
