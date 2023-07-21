import collections.abc
import contextlib
from types import NoneType, UnionType
from typing import (
    Any,
    ForwardRef,
    Generic,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from typing_extensions import override

from bolinette.core import types
from bolinette.core.exceptions import TypingError

T = TypeVar("T")


class Type(Generic[T]):
    __slots__ = ("cls", "vars", "annotations", "nullable", "union")

    @staticmethod
    def from_instance(__instance: T) -> "Type[T]":
        return Type(type(__instance))

    def __init__(
        self,
        __cls: type[T],
        *,
        lookup: "types.TypeVarLookup[Any] | None" = None,
        raise_on_string: bool = True,
        raise_on_typevar: bool = True,
    ) -> None:
        if get_origin(__cls) in (Union, UnionType):
            args = get_args(__cls)
            self.nullable = None in args or NoneType in args
            args = tuple(a for a in args if a not in (None, NoneType))
            __cls, *additional_cls = args
        else:
            additional_cls = ()
            self.nullable = False
        self.cls, self.vars = Type.get_generics(__cls, lookup, raise_on_string, raise_on_typevar)
        self.vars = (*self.vars, *map(lambda _: Any, range(len(self.vars), self.get_param_count(self.cls))))
        self.annotations = Type._get_recursive_annotations(self.cls)
        self.union = tuple(Type(c) for c in additional_cls)

    @override
    def __str__(self) -> str:
        def _format_v(v: type[Any] | TypeVar | ForwardRef) -> str:
            if isinstance(v, type):
                return v.__qualname__
            if isinstance(v, TypeVar):
                return f"~{v.__name__}"
            if v is Ellipsis:
                return "..."
            return f"'{str(v.__forward_arg__)}'"

        if not self.vars:
            repr_str = _format_v(self.cls)
        else:
            repr_str = f"{_format_v(self.cls)}[{', '.join(map(_format_v, self.vars))}]"

        if self.is_union:
            for t in self.union:
                repr_str += f" | {str(t)}"

        if self.nullable:
            repr_str += " | None"

        return repr_str

    @override
    def __repr__(self) -> str:
        return f"<Type {str(self)}>"

    @override
    def __hash__(self) -> int:
        return hash((self.cls, self.vars))

    @override
    def __eq__(self, __value: object) -> bool:
        return (
            isinstance(__value, Type)
            and __value.cls is self.cls  # pyright: ignore[reportUnknownMemberType]
            and __value.vars == self.vars
        )

    def new(self, *args: Any, **kwargs: Any) -> T:
        return self.cls(*args, **kwargs)

    @property
    def is_union(self) -> bool:
        return len(self.union) > 0

    @property
    def is_any(self) -> bool:
        return self.cls is Any

    @staticmethod
    def _get_recursive_annotations(_cls: type[Any]) -> "dict[str, Type[Any]]":
        annotations: dict[str, Type[Any]] = {}
        try:
            for base in _cls.__bases__:
                annotations |= Type._get_recursive_annotations(base)
            hints: dict[str, type[Any]] = get_type_hints(_cls)
            for attr_name, hint in hints.items():
                annotations[attr_name] = Type(hint)
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
                type_vars = (*type_vars, arg)
            return origin, type_vars
        return _cls, ()

    @staticmethod
    def get_param_count(__cls: type[Any]) -> int:
        if __cls in _BUILTIN_PARAM_COUNT:
            return _BUILTIN_PARAM_COUNT[__cls]
        if hasattr(__cls, "__parameters__"):
            return len(__cls.__parameters__)  # type: ignore
        return 0


_BUILTIN_PARAM_COUNT: dict[type[Any], int] = {
    collections.abc.Hashable: 0,
    collections.abc.Awaitable: 1,
    collections.abc.Coroutine: 3,
    collections.abc.AsyncIterable: 1,
    collections.abc.AsyncIterator: 1,
    collections.abc.Iterable: 1,
    collections.abc.Iterator: 1,
    collections.abc.Reversible: 1,
    collections.abc.Sized: 0,
    collections.abc.Container: 1,
    collections.abc.Collection: 1,
    collections.abc.Set: 1,
    collections.abc.MutableSet: 1,
    collections.abc.Mapping: 2,
    collections.abc.MutableMapping: 2,
    collections.abc.Sequence: 1,
    collections.abc.MutableSequence: 1,
    collections.abc.ByteString: 0,
    list: 1,
    collections.deque: 1,
    set: 1,
    frozenset: 1,
    collections.abc.MappingView: 1,
    collections.abc.KeysView: 1,
    collections.abc.ItemsView: 2,
    collections.abc.ValuesView: 1,
    contextlib.AbstractContextManager: 1,
    contextlib.AbstractAsyncContextManager: 1,
    dict: 2,
    collections.defaultdict: 2,
    collections.OrderedDict: 2,
    collections.Counter: 1,
    collections.ChainMap: 2,
    collections.abc.Generator: 3,
    collections.abc.AsyncGenerator: 2,
    type: 1,
}
