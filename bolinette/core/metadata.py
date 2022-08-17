from typing import Any, TypeVar

from bolinette.core.exceptions import InternalError

T = TypeVar("T")


class _BolinetteMetadata:
    def __init__(self) -> None:
        self._data: dict[type[Any], Any] = {}

    def __contains__(self, key: type[Any]) -> bool:
        if not isinstance(key, type):
            raise TypeError(f"Metadata key {key} must be a type")
        return key in self._data

    def __getitem__(self, key: type[T]) -> T:
        if not key in self:
            raise KeyError(key)
        return self._data[key]

    def __setitem__(self, key: type[T], value: T) -> None:
        if not isinstance(key, type):
            raise TypeError(f"Metadata key {key} must be a type")
        if not isinstance(value, key):
            raise TypeError(f"Type mismatch between {key} and {value}")
        self._data[key] = value


def _get_meta_container(obj: Any) -> _BolinetteMetadata:
    if "__blnt_meta__" not in vars(obj):
        meta = _BolinetteMetadata()
        setattr(obj, "__blnt_meta__", meta)
    else:
        meta = getattr(obj, "__blnt_meta__")
        if not isinstance(meta, _BolinetteMetadata):
            raise InternalError(
                f"Metadata container in {obj} has been overwritten. "
                "Please do not use '__blnt_meta__' as an attribute in any class"
            )
    return meta


class _MetaFunctions:
    @staticmethod
    def has(obj: Any, cls: type[Any], /) -> bool:
        if not hasattr(obj, "__dict__"):
            return False
        if not isinstance(cls, type):
            raise TypeError(f"Argument {cls} must be a type")
        container = _get_meta_container(obj)
        return cls in container

    @staticmethod
    def set(obj: Any, meta: T, /, *, cls: type[T] | None = None) -> None:
        if cls is None:
            cls = type(meta)
        else:
            if not isinstance(cls, type):
                raise TypeError(f"Argument {cls} must be a type")
            if not isinstance(meta, cls):
                raise TypeError(f"Type mismatch between {cls} and {meta}")
        container = _get_meta_container(obj)
        container[cls] = meta

    @staticmethod
    def get(obj: Any, cls: type[T], /, *, default: T | None = None) -> T:
        if not isinstance(cls, type):
            raise TypeError(f"Argument {cls} must be a type")
        container = _get_meta_container(obj)
        if cls not in container and default is not None:
            return default
        return container[cls]


meta = _MetaFunctions()
