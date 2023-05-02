from types import UnionType
from typing import Any, ForwardRef, Generic, TypeVar, Union, get_args, get_origin, get_type_hints

from bolinette import types
from bolinette.exceptions import TypingError

T = TypeVar("T")


class Type(Generic[T]):
    __slots__ = ("cls", "vars")

    def __init__(
        self,
        __cls: type[T],
        *,
        lookup: "types.TypeVarLookup | None" = None,
        raise_on_string: bool = True,
        raise_on_typevar: bool = True,
    ) -> None:
        self.cls, self.vars = Type.get_generics(__cls, lookup, raise_on_string, raise_on_typevar)
        if hasattr(self.cls, "__parameters__") and len(self.cls.__parameters__) != len(self.vars):  # type:ignore
            raise TypingError("All generic parameters must be defined", cls=self.cls.__qualname__)

    def __str__(self) -> str:
        def _format_v(v: type[Any] | TypeVar | ForwardRef) -> str:
            if isinstance(v, type):
                return v.__qualname__
            if isinstance(v, TypeVar):
                return f"~{v.__name__}"
            return f"'{str(v.__forward_arg__)}'"

        if not self.vars:
            return _format_v(self.cls)
        return f"{_format_v(self.cls)}[{', '.join(map(_format_v, self.vars))}]"

    def __repr__(self) -> str:
        return f"<Type {str(self)}>"

    def __hash__(self) -> int:
        return hash((self.cls, self.vars))

    def __eq__(self, __value: object) -> bool:
        return isinstance(__value, Type) and __value.cls is self.cls and __value.vars == self.vars

    @staticmethod
    def _get_recursive_annotations(_cls: type[Any]):
        annotations: dict[str, tuple[type[Any] | None, ...]] = {}
        for base in _cls.__bases__:
            annotations |= Type._get_recursive_annotations(base)
        hints: dict[str, type[Any]] = get_type_hints(_cls)
        for attr_name, hint in hints.items():
            if get_origin(hint) in (UnionType, Union):
                annotations[attr_name] = tuple(h if h is not type(None) else None for h in get_args(hint))
            else:
                annotations[attr_name] = (hint,)
        return annotations

    def get_annotations(self) -> dict[str, tuple[type[Any] | None, ...]]:
        return Type._get_recursive_annotations(self.cls)

    @staticmethod
    def get_generics(
        _cls: type[T],
        lookup: "types.TypeVarLookup | None",
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
