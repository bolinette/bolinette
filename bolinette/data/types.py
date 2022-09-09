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


String = DataType("String", _sqlalchemy.String, str)
Integer = DataType("Integer", _sqlalchemy.Integer, int)
Float = DataType("Float", _sqlalchemy.Float, float)
Boolean = DataType("Boolean", _sqlalchemy.Boolean, bool)
Date = DataType("Date", _sqlalchemy.DateTime, datetime)
Email = DataType("Email", _sqlalchemy.String, str)
Password = DataType("Password", _sqlalchemy.String, str)
