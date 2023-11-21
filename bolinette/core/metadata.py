from typing import Any

from bolinette.core.exceptions import InternalError


class BolinetteMetadata:
    def __init__(self) -> None:
        self._data: dict[type[Any], Any] = {}

    def __contains__(self, key: type[Any]) -> bool:
        return key in self._data

    def __getitem__[T](self, key: type[T]) -> T:
        if key not in self:
            raise KeyError(key)
        return self._data[key]

    def __setitem__[T](self, key: type[T], value: T) -> None:
        if not isinstance(value, key):
            raise TypeError(f"Type mismatch between {key} and {value}")
        self._data[key] = value


def get_meta_container(obj: Any) -> BolinetteMetadata:
    if "__blnt_meta__" not in vars(obj):
        _meta = BolinetteMetadata()
        obj.__blnt_meta__ = _meta
    else:
        _meta = obj.__blnt_meta__
        if not isinstance(_meta, BolinetteMetadata):
            raise InternalError(
                f"Metadata container in {obj} has been overwritten. "
                "Please do not use '__blnt_meta__' as an attribute in any class"
            )
    return _meta


class _MetaFunctions:
    @staticmethod
    def has(obj: Any, cls: type[Any], /) -> bool:
        if not hasattr(obj, "__dict__"):
            return False
        container = get_meta_container(obj)
        return cls in container

    @staticmethod
    def set[T](obj: Any, _meta: T, /, *, cls: type[T] | None = None) -> None:
        if cls is None:
            cls = type(_meta)
        else:
            if not isinstance(_meta, cls):
                raise TypeError(f"Type mismatch between {cls} and {_meta}")
        container = get_meta_container(obj)
        container[cls] = _meta

    @staticmethod
    def get[T](obj: Any, cls: type[T], /, *, default: T | None = None) -> T:
        container = get_meta_container(obj)
        if cls not in container and default is not None:
            return default
        return container[cls]


meta = _MetaFunctions()
