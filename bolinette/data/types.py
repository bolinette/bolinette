from datetime import datetime
from typing import Any

import sqlalchemy as _sqlalchemy


class DataType:
    def __init__(self, name: str, sqlalchemy_type, python_type: type[Any]) -> None:
        self.name = name
        self.sqlalchemy_type = sqlalchemy_type
        self.python_type = python_type

    def of_type(self, cls) -> bool:
        return type(self) is cls

    def __repr__(self) -> str:
        return self.name


_all_types: dict[type[Any], Any] = {
    str: _sqlalchemy.String,
    int: _sqlalchemy.Integer,
    float: _sqlalchemy.Float,
    bool: _sqlalchemy.Boolean,
    datetime: _sqlalchemy.DateTime,
}


def is_supported(py_type: type[Any]) -> bool:
    return py_type in _all_types


def get_sql_type(py_type: type[Any]) -> Any:
    if not is_supported(py_type):
        raise KeyError(py_type)
    return _all_types[py_type]
