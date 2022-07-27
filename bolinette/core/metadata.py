from typing import Any, TypeVar

from bolinette.core.exceptions import InternalError

_T = TypeVar("_T")


class _BolinetteMetadata:
    def __init__(self) -> None:
        self._data: dict[type[Any], Any] = {}

    def __contains__(self, key: type[Any]) -> bool:
        if not isinstance(key, type):
            raise TypeError(f"Metadata key {key} must be a type")
        return key in self._data

    def __getitem__(self, key: type[_T]) -> _T:
        if not key in self:
            raise KeyError(key)
        return self._data[key]

    def __setitem__(self, key: type[_T], value: _T) -> None:
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
    def has(__obj: Any, __meta_cls: type[Any]) -> bool:
        if not isinstance(__meta_cls, type):
            raise TypeError(f"Argument {__meta_cls} must be a type")
        meta = _get_meta_container(__obj)
        return __meta_cls in meta

    @staticmethod
    def set(__obj: Any, __meta_cls: type[Any], __meta: Any) -> None:
        if not isinstance(__meta_cls, type):
            raise TypeError(f"Argument {__meta_cls} must be a type")
        if not isinstance(__meta, __meta_cls):
            raise TypeError(f"Type mismatch between {__meta_cls} and {__meta}")
        meta = _get_meta_container(__obj)
        meta[__meta_cls] = __meta

    @staticmethod
    def get(__obj: Any, __meta_cls: type[_T]) -> _T:
        if not isinstance(__meta_cls, type):
            raise TypeError(f"Argument {__meta_cls} must be a type")
        meta = _get_meta_container(__obj)
        return meta[__meta_cls]


meta = _MetaFunctions()
