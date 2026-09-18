from collections.abc import Awaitable, Callable
from typing import Any, overload

from escondite import Cache
from peritype import wrap_func

from bolinette.core import meta
from bolinette.core.commands._meta import CommandMeta


def _set_meta(
    cache: Cache,
    func: Callable[..., Awaitable[int | None]],
    name: str,
    summary: str,
    run_startup: bool,
) -> None:
    meta.set(func, CommandMeta.KEY, CommandMeta(name, summary, run_startup))
    Cache.with_fallback(cache).add(CommandMeta.KEY, wrap_func(func))


@overload
def command[**P](
    func: Callable[P, Awaitable[int | None]],
    name: str,
    summary: str,
    /,
    *,
    cache: Cache | None = None,
    run_startup: bool = True,
) -> Callable[P, Awaitable[int | None]]: ...
@overload
def command[**P](
    name: str,
    summary: str,
    /,
    *,
    cache: Cache | None = None,
    run_startup: bool = True,
) -> Callable[..., Callable[P, Awaitable[int | None]]]: ...
def command(
    *args: Any,
    cache: Cache | None = None,
    run_startup: bool = True,
) -> Any:
    cache = Cache.with_fallback(cache)
    match args:
        case (str() as name, str() as summary):

            def decorator(func: Callable[..., Awaitable[int | None]]) -> Callable[..., Awaitable[int | None]]:
                _set_meta(cache, func, name, summary, run_startup)
                return func

            return decorator
        case (func, str() as name, str() as summary):
            _set_meta(cache, func, name, summary, run_startup)
            return func
        case _:
            raise TypeError
