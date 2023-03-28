from types import UnionType
from typing import TYPE_CHECKING, Any, ForwardRef, Protocol, TypeVar, Union, get_args, get_origin, get_type_hints

from bolinette.exceptions import InternalError

InstanceT = TypeVar("InstanceT")


class AttributeUtils:
    @staticmethod
    def get_cls_attrs(
        obj: type[Any], *, of_type: type[InstanceT] | tuple[type[InstanceT], ...] | None = None
    ) -> dict[str, InstanceT]:
        parent_attrs = {}
        for parent in obj.__bases__:
            parent_attrs |= AttributeUtils.get_cls_attrs(parent, of_type=of_type)
        return parent_attrs | {
            name: attribute
            for name, attribute in vars(obj).items()
            if of_type is None or isinstance(attribute, of_type)
        }

    @staticmethod
    def get_instance_attrs(obj: object, *, of_type: type[InstanceT] | None = None) -> dict[str, InstanceT]:
        return {
            name: attribute
            for name, attribute in vars(obj).items()
            if of_type is None or isinstance(attribute, of_type)
        }

    @staticmethod
    def get_all_annotations(__cls: type[Any]) -> dict[str, tuple[type[Any] | None]]:
        annotations: dict[str, tuple[type[Any] | None]] = {}
        for base in __cls.__bases__:
            annotations |= AttributeUtils.get_all_annotations(base)
        hints: dict[str, type[Any]] = get_type_hints(__cls)
        for attr_name, hint in hints.items():
            if get_origin(hint) in (UnionType, Union):
                annotations[attr_name] = tuple(h if h is not type(None) else None for h in get_args(hint))
            else:
                annotations[attr_name] = (hint,)
        return annotations

    @staticmethod
    def get_generics(
        _cls: type[InstanceT],
        *,
        typevar_lookup: dict[TypeVar, type[Any]] | None = None,
        raise_on_string: bool = False,
        raise_on_typevar: bool = False,
    ) -> tuple[type[InstanceT], tuple[Any, ...]]:
        if origin := get_origin(_cls):
            type_vars: tuple[Any, ...] = ()
            for arg in get_args(_cls):
                if isinstance(arg, ForwardRef) and raise_on_string:
                    raise InternalError("String literal generic parameters are not allowed in this context")
                if isinstance(arg, TypeVar):
                    if raise_on_typevar:
                        raise InternalError("Generic type vars are not allowed in this context")
                    if typevar_lookup is not None and arg in typevar_lookup:
                        arg = typevar_lookup[arg]
                type_vars = (*type_vars, arg)
            return origin, type_vars
        return _cls, ()

    @staticmethod
    def get_typevar_lookup(_cls: type[Any], type_vars: tuple[Any, ...]) -> dict[TypeVar, type[Any]] | None:
        if not hasattr(_cls, "__parameters__"):
            return None
        if TYPE_CHECKING:
            assert isinstance(_cls, _GenericOrigin)
        return {n: type_vars[i] for i, n in enumerate(_cls.__parameters__)}


class _GenericOrigin(Protocol):
    __parameters__: tuple[TypeVar, ...]
