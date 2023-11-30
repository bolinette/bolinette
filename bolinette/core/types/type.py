import collections.abc
import contextlib
import inspect
from types import NoneType, UnionType
from typing import (
    Annotated,
    Any,
    ForwardRef,
    Literal,
    TypeGuard,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    override,
)

from bolinette.core import types
from bolinette.core.exceptions import TypingError


class Type[T]:
    __slots__: list[str] = ["cls", "vars", "nullable", "union", "annotated", "_hash"]

    @staticmethod
    def from_instance(__instance: T) -> "Type[T]":
        return Type(type(__instance))

    def __init__(
        self,
        cls: type[T],
        /,
        *,
        lookup: "types.TypeVarLookup[Any] | None" = None,
        raise_on_string: bool = True,
        raise_on_typevar: bool = True,
    ) -> None:
        self.annotated: tuple[Any, ...]
        if get_origin(cls) is Annotated:
            cls, *self.annotated = get_args(cls)
        else:
            self.annotated = ()
        if get_origin(cls) in (Union, UnionType):
            args = get_args(cls)
            self.nullable = None in args or NoneType in args
            args = tuple(a for a in args if a not in (None, NoneType))
            cls, *additional_cls = args
        else:
            additional_cls = ()
            self.nullable = False
        self.cls, self.vars = Type.get_generics(cls, lookup, raise_on_string, raise_on_typevar)
        self.vars = (*self.vars, *map(lambda _: Any, range(len(self.vars), Type.get_param_count(self.cls))))
        self.union = tuple(Type(c) for c in additional_cls)
        self._hash = hash((self.cls, self.vars))

    @override
    def __str__(self) -> str:
        def _format_v(v: Any) -> str:
            if isinstance(v, type):
                return v.__qualname__
            if isinstance(v, TypeVar):
                return f"~{v.__name__}"
            if v is Ellipsis:
                return "..."
            if v is Literal:
                return v.__name__
            if isinstance(v, ForwardRef):
                return f"'{v.__forward_arg__}'"
            return str(v)

        if not self.vars:
            repr_str = _format_v(self.cls)
        else:
            repr_str = f"{_format_v(self.cls)}[{', '.join(map(_format_v, self.vars))}]"

        if self.is_union:
            for t in self.union:
                repr_str += f" | {t}"

        if self.nullable:
            repr_str += " | None"

        return repr_str

    @override
    def __repr__(self) -> str:
        return f"<Type {self}>"

    @override
    def __hash__(self) -> int:
        return self._hash

    @override
    def __eq__(self, __value: object) -> bool:
        return (
            isinstance(__value, Type)
            and __value.cls is self.cls  # pyright: ignore[reportUnknownMemberType]
            and __value.vars == self.vars
        )

    @property
    def init(self):
        return types.Function(self.cls.__init__)

    @property
    def is_union(self) -> bool:
        return len(self.union) > 0

    @property
    def is_any(self) -> bool:
        return self.cls is Any

    def new(self, *args: Any, **kwargs: Any) -> T:
        return self.cls(*args, **kwargs)

    def parameters(self) -> dict[str, inspect.Parameter]:
        return {**inspect.signature(self.cls).parameters}

    def annotations(self, *, lookup: "types.TypeVarLookup[Any] | None" = None) -> "dict[str, Type[Any]]":
        return self._get_recursive_annotations(self.cls, lookup)

    def isinstance(self, instance: Any) -> TypeGuard[T]:
        return isinstance(instance, self.cls)

    @staticmethod
    def _get_recursive_annotations(
        _cls: type[Any], lookup: "types.TypeVarLookup[Any] | None"
    ) -> "dict[str, Type[Any]]":
        annotations: dict[str, Type[Any]] = {}
        try:
            for base in _cls.__bases__:
                annotations |= Type._get_recursive_annotations(base, lookup)
            hints: dict[str, type[Any]] = get_type_hints(_cls)
            for attr_name, hint in hints.items():
                annotations[attr_name] = Type(hint, lookup=lookup)
        except (AttributeError, TypeError, NameError):
            return annotations
        return annotations

    @staticmethod
    def get_generics(
        _cls: type[T],
        lookup: "types.TypeVarLookup[Any] | None",
        raise_on_string: bool,
        raise_on_typevar: bool,
    ) -> tuple[type[T], tuple[Any, ...]]:
        if origin := get_origin(_cls):
            type_vars: tuple[Any, ...] = ()
            for arg in get_args(_cls):
                arg: Any
                if isinstance(arg, ForwardRef) and raise_on_string:
                    raise TypingError(
                        f"Generic parameter '{arg.__forward_arg__}' cannot be a string", cls=origin.__qualname__
                    )
                if isinstance(arg, TypeVar):
                    if lookup is not None:
                        if arg in lookup:
                            arg = lookup[arg]
                        elif raise_on_typevar:
                            raise TypingError(
                                f"TypeVar ~{arg.__name__} could not be found in lookup", cls=origin.__qualname__
                            )
                    elif raise_on_typevar:
                        raise TypingError(
                            f"Generic parameter ~{arg.__name__} cannot be a TypeVar", cls=origin.__qualname__
                        )
                if isinstance(arg, list):
                    arg = tuple(*arg)  # pyright: ignore[reportUnknownArgumentType]
                type_vars = (*type_vars, arg)
            return origin, type_vars
        return _cls, ()

    @staticmethod
    def get_param_count(cls_: type[Any]) -> int:
        if cls_ in _BUILTIN_PARAM_COUNT:
            return _BUILTIN_PARAM_COUNT[cls_]
        if hasattr(cls_, "__parameters__"):
            return len(cls_.__parameters__)  # pyright: ignore
        return 0


_BUILTIN_PARAM_COUNT: dict[type[Any], int] = {
    collections.abc.Hashable: 0,
    collections.abc.Awaitable: 1,  # pyright: ignore
    collections.abc.Coroutine: 3,  # pyright: ignore
    collections.abc.AsyncIterable: 1,  # pyright: ignore
    collections.abc.AsyncIterator: 1,  # pyright: ignore
    collections.abc.Iterable: 1,  # pyright: ignore
    collections.abc.Iterator: 1,  # pyright: ignore
    collections.abc.Reversible: 1,  # pyright: ignore
    collections.abc.Sized: 0,
    collections.abc.Container: 1,  # pyright: ignore
    collections.abc.Collection: 1,  # pyright: ignore
    collections.abc.Set: 1,  # pyright: ignore
    collections.abc.MutableSet: 1,  # pyright: ignore
    collections.abc.Mapping: 2,  # pyright: ignore
    collections.abc.MutableMapping: 2,  # pyright: ignore
    collections.abc.Sequence: 1,  # pyright: ignore
    collections.abc.MutableSequence: 1,  # pyright: ignore
    list: 1,
    collections.deque: 1,  # pyright: ignore
    set: 1,
    frozenset: 1,
    collections.abc.MappingView: 1,
    collections.abc.KeysView: 1,  # pyright: ignore
    collections.abc.ItemsView: 2,  # pyright: ignore
    collections.abc.ValuesView: 1,  # pyright: ignore
    contextlib.AbstractContextManager: 1,  # pyright: ignore
    contextlib.AbstractAsyncContextManager: 1,  # pyright: ignore
    dict: 2,
    collections.defaultdict: 2,  # pyright: ignore
    collections.OrderedDict: 2,  # pyright: ignore
    collections.Counter: 1,  # pyright: ignore
    collections.ChainMap: 2,  # pyright: ignore
    collections.abc.Generator: 3,  # pyright: ignore
    collections.abc.AsyncGenerator: 2,  # pyright: ignore
    type: 1,
}
