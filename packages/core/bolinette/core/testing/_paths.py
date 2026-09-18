import contextlib
import functools
import os
from collections.abc import Awaitable, Callable, Generator
from tempfile import TemporaryDirectory
from typing import Any


@contextlib.contextmanager
def tmp_cwd() -> Generator[str, Any]:
    original_cwd = os.getcwd()
    with TemporaryDirectory() as tmp_dir:
        os.chdir(tmp_dir)
        try:
            yield tmp_dir
        finally:
            os.chdir(original_cwd)


def with_tmp_cwd[**P, T](func: Callable[P, T]) -> Callable[P, T]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        with tmp_cwd():
            return func(*args, **kwargs)

    return wrapper


def with_tmp_cwd_async[**P, T](func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        with tmp_cwd():
            return await func(*args, **kwargs)

    return wrapper
