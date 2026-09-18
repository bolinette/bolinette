from collections.abc import Callable
from typing import Any, overload


@overload
def get_cls_attrs(cls: type[Any], /, *, of_type: None = None) -> dict[str, Any]: ...


@overload
def get_cls_attrs[AttrT](cls: type[Any], /, *, of_type: type[AttrT]) -> dict[str, AttrT]: ...


def get_cls_attrs[AttrT](cls: type[Any], /, *, of_type: type[AttrT] | None = None) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    for parent in cls.__bases__:
        attrs |= get_cls_attrs(parent, of_type=of_type)
    return attrs | {
        name: attribute for name, attribute in vars(cls).items() if of_type is None or isinstance(attribute, of_type)
    }


def instance_resolver[T](interface: Any, instance: T) -> Callable[[], T]:

    def _resolve() -> T:
        return instance

    _resolve.__annotations__ = {"return": interface}
    return _resolve
