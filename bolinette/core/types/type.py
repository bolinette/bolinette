import collections.abc
import contextlib
import inspect
from types import NoneType, UnionType
from typing import (
    Annotated,
    Any,
    ForwardRef,
    Generic,
    Literal,
    NotRequired,
    TypeAliasType,
    TypeGuard,
    TypeVar,
    get_args,
    get_origin,
    get_type_hints,
    override,
)

from bolinette.core import types
from bolinette.core.exceptions import TypingError


class Type[T]:
    __slots__: list[str] = [
        "origin",
        "cls",
        "vars",
        "lookup",
        "nullable",
        "union",
        "annotated",
        "required",
        "total",
        "_hash",
        "_bases",
    ]

    origin: type[T]
    annotated: tuple[Any, ...]
    required: bool
    nullable: bool
    union: "tuple[Type[Any], ...]"
    total: bool
    cls: type[T]
    vars: tuple[Any, ...]
    lookup: "types.TypeVarLookup[T]"

    @staticmethod
    def from_instance(__instance: T) -> "Type[T]":
        return Type(type(__instance))

    def __init__(
        self,
        origin: type[T],
        /,
        *,
        lookup: "types.TypeVarMapping | None" = None,
        raise_on_string: bool = True,
        raise_on_typevar: bool = True,
    ) -> None:
        self.origin = origin
        self.annotated = ()
        self.required = True
        self.nullable = False
        self.union = ()
        cls = self._unpack_annotations(origin)
        self.total = getattr(cls, "__total__", True)
        self.cls, self.vars = Type.get_generics(cls, lookup, raise_on_string, raise_on_typevar)
        self.vars = (
            *self.vars,
            *map(lambda _: Any, range(len(self.vars), Type.get_param_count(self.cls))),
        )
        self.lookup = types.TypeVarLookup(self)
        self._hash = hash((self.cls, self.vars))
        self._bases: tuple[Type[Any], ...] | None = None

    def _unpack_annotations(self, cls: type[T]) -> type[T]:
        if isinstance(cls, TypeAliasType):
            return self._unpack_annotations(cls.__value__)
        origin = get_origin(cls)
        if origin is Annotated:
            cls, *self.annotated = get_args(cls)
            return self._unpack_annotations(cls)
        if origin is NotRequired:
            self.required = False
            return self._unpack_annotations(get_args(cls)[0])
        if origin is UnionType:
            args = get_args(cls)
            self.nullable = None in args or NoneType in args
            args = tuple(a for a in args if a not in (None, NoneType))
            cls, *additional_cls = args
            self.union = tuple(Type(c) for c in additional_cls)
            return self._unpack_annotations(cls)
        return cls

    @staticmethod
    def _format_type(v: Any) -> str:
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

    @property
    def base_name(self) -> str:
        return self._format_type(self.cls)

    @property
    def bases(self) -> "tuple[Type[Any], ...]":
        if self._bases is None:
            if hasattr(self.cls, "__orig_bases__"):
                self._bases = tuple(
                    Type(c, lookup=self.lookup)
                    for c in self.cls.__orig_bases__  # pyright: ignore
                    if get_origin(c) is not Generic  # pyright: ignore
                )
            else:
                self._bases = tuple(Type(c, lookup=self.lookup) for c in self.cls.__bases__)
        return self._bases

    @override
    def __str__(self) -> str:
        if not self.vars:
            repr_str = self._format_type(self.cls)
        else:
            repr_str = f"{self._format_type(self.cls)}[{', '.join(map(self._format_type, self.vars))}]"

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

    def annotations(self) -> "dict[str, Type[Any]]":
        return self._get_recursive_annotations(self.cls)

    def isinstance(self, instance: Any) -> TypeGuard[T]:
        return isinstance(instance, self.cls)

    def _get_recursive_annotations(self, _cls: type[Any]) -> "dict[str, Type[Any]]":
        annotations: dict[str, Type[Any]] = {}
        try:
            for base in _cls.__bases__:
                annotations |= self._get_recursive_annotations(base)
            hints: dict[str, type[Any] | TypeVar] = get_type_hints(_cls, include_extras=True)
            for attr_name, hint in hints.items():
                if isinstance(hint, TypeVar):
                    if hint in self.lookup:
                        annotations[attr_name] = Type(self.lookup[hint])
                    else:
                        raise TypingError(
                            f"TypeVar ~{hint.__name__} could not be found in lookup", cls=_cls.__qualname__
                        )
                else:
                    annotations[attr_name] = Type(hint, lookup=self.lookup)
        except (AttributeError, TypeError, NameError):
            return annotations
        return annotations

    def matches(self, t: "Type[Any]") -> bool:
        if self.cls is not t.cls or len(self.vars) != len(t.vars):
            return False
        for v1, v2 in zip(self.vars, t.vars, strict=True):
            if v1 is not Any and v2 is not Any and v1 != v2:
                return False
        return True

    @staticmethod
    def get_generics[GenT](
        _cls: type[GenT],
        lookup: "types.TypeVarMapping | None",
        raise_on_string: bool,
        raise_on_typevar: bool,
    ) -> tuple[type[GenT], tuple[Any, ...]]:
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
            return len(cls_.__parameters__)
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
