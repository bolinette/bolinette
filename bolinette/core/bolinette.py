from typing import Callable

from bolinette.core import Context, Injection, __core_cache__
from bolinette.core.utils import paths


class Bolinette:
    def __init__(
        self, *, context: Context | None = None, inject: Injection | None = None
    ) -> None:
        self._context = context or Context(paths.dirname(__file__))
        self._inject = inject or Injection(__core_cache__)
        self._inject.add(Bolinette, self)
        self._inject.add(Context, self._context)

    async def startup(self) -> None:
        for func in __core_cache__.init_funcs:
            print(f"[INIT]: Running {func.name}")
            await self._inject.call(func.function)


def main_func(func: Callable[[], Bolinette]) -> Callable[[], Bolinette]:
    setattr(func, "__blnt__", "__blnt_main__")
    return func
