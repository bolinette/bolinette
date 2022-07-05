from typing import Callable

from bolinette.core import Context, Injection, __core_cache__
from bolinette.core.utils import paths


class Bolinette:
    def __init__(self):
        self._context = Context(paths.dirname(__file__))
        self._inject = Injection()

    async def startup(self) -> None:
        self._inject.add(Bolinette, self)
        self._inject.add(Context, self._context)
        for func in __core_cache__.init_funcs:
            print(f"[INIT]: Running {func.name}")
            await self._inject.call(func.function)


def main_func(func: Callable[[], Bolinette]):
    setattr(func, "__blnt__", "__blnt_main__")
    return func
