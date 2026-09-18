import datetime
import decimal
import pathlib
import uuid
from enum import Enum
from types import NoneType
from typing import Any, Final

from peritype import TWrap, wrap_type

_SCALAR_TYPES: Final = (int, float, str, bytes, bool, complex)
_VALUE_TYPES: Final = (
    datetime.datetime,
    datetime.date,
    datetime.time,
    datetime.timedelta,
    uuid.UUID,
    decimal.Decimal,
    pathlib.PurePath,
    Enum,
)


def main_class(t: TWrap[Any]) -> type[Any] | None:
    if t.union:
        return None
    cls: Any = t.inner_type
    return cls if isinstance(cls, type) and cls not in (NoneType, Any) else None


def is_value_type(t: TWrap[Any]) -> bool:
    cls = main_class(t)
    if cls is None:
        return True
    return issubclass(cls, _SCALAR_TYPES) or issubclass(cls, _VALUE_TYPES) or cls is NoneType


def dict_value_type(t: TWrap[Any]) -> TWrap[Any]:
    cls = main_class(t)
    if cls is None or not issubclass(cls, dict):
        return wrap_type(Any)
    node = next(n for n in t.nodes if n.inner_type is cls)
    return node.generic_params[1] if len(node.generic_params) > 1 else wrap_type(Any)


def element_type(t: TWrap[Any]) -> TWrap[Any] | None:
    cls = main_class(t)
    if cls is None or not issubclass(cls, (list, set, frozenset, tuple)):
        return None
    node = next(n for n in t.nodes if n.inner_type is cls)
    return node.generic_params[0] if node.generic_params else wrap_type(Any)
