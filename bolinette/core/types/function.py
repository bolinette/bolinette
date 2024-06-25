import inspect
from collections.abc import Callable
from types import NoneType
from typing import Any, get_type_hints, override

from bolinette.core.types import Type, TypeVarLookup


class Function[**FuncP, FuncT]:
    __slots__: list[str] = ["func", "bound_to"]

    def __init__(self, func: Callable[FuncP, FuncT]) -> None:
        if isinstance(func, Function):
            raise TypeError(f"Cannot wrap {func}, already wrapped")
        self.func = func
        self.bound_to = getattr(self.func, "__self__", None)

    @property
    def name(self) -> str:
        return self.func.__name__ if hasattr(self.func, "__name__") else str(self.func)

    def parameters(self) -> dict[str, inspect.Parameter]:
        return {**inspect.signature(self.func).parameters}

    def annotations(self, *, lookup: TypeVarLookup[Any] | None = None) -> dict[str, Any]:
        return {
            n: self._transform_annotation(c, lookup) for n, c in get_type_hints(self.func, include_extras=True).items()
        }

    def __call__(self, *args: FuncP.args, **kwargs: FuncP.kwargs) -> FuncT:
        return self.func(*args, **kwargs)

    @staticmethod
    def _transform_annotation(anno: Any, lookup: TypeVarLookup[Any] | None) -> Any:
        if lookup is not None and anno in lookup:
            return Type(lookup[anno], lookup=lookup)
        if anno in (NoneType, Ellipsis):
            return anno
        return Type(anno, lookup=lookup)

    @override
    def __str__(self) -> str:
        return f"{self.func.__qualname__}"

    @override
    def __repr__(self) -> str:
        return f"<Function {self}>"

    @override
    def __hash__(self) -> int:
        return hash(self.func)
