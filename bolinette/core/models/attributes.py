from typing import Union, Literal, Optional, Any, Dict

from bolinette import types, core
from bolinette.exceptions import InitError


class Reference:
    def __init__(self, model: 'core.Model', column: 'core.models.Column', models: Dict[str, 'core.Model'],
                 model_name: str, column_name: str):
        self.model = model
        self.column = column
        if model_name not in models:
            raise InitError(f'{model.__blnt__.name}.{column.name}: unknown "{model_name}" model')
        self.target_model = models[model_name]
        target_cols = dict(self.target_model.__props__.get_columns())
        if column_name not in target_cols:
            raise InitError(f'{model.__blnt__.name}.{column.name}: no "{column_name}" column in "{model_name}" model')
        self.target_column = target_cols[column_name]

    @property
    def model_name(self):
        return self.model.__blnt__.name

    @property
    def column_name(self):
        return self.column.name

    @property
    def target_model_name(self):
        return self.target_model.__blnt__.name

    @property
    def target_column_name(self):
        return self.target_column.name

    @property
    def target_path(self):
        return f'{self.target_model_name}.{self.target_column_name}'

    def __repr__(self):
        return f'<Reference {self.model_name}.{self.column_name} -> {self.target_path}>'


class Column:
    def __init__(self, name: str, model: 'core.Model', data_type: 'types.db.DataType', reference: Optional[Reference],
                 primary_key: bool, nullable: bool, unique: bool, model_id: bool, default: Optional[Any]):
        self.name = name
        self.type = data_type
        self.model = model
        self.reference = reference
        self.primary_key = primary_key
        self.nullable = nullable
        self.unique = unique
        self.model_id = model_id
        self.default = default

    @property
    def model_name(self):
        return self.model.__blnt__.name

    def __repr__(self):
        s = f'<Column {self.model_name}.{self.name}: {repr(self.type)}'
        if self.reference is not None:
            s += f' -> {self.reference.target_path}'
        return s + '>'


class ColumnList:
    def __init__(self, name: str, model: 'core.Model', origin: 'core.Model'):
        self.name = name
        self.model = model
        self.origin = origin


class Backref:
    def __init__(self, model: 'core.Model', relationship: 'core.models.Relationship',
                 key: str, lazy: bool):
        self.model = model
        self.relationship = relationship
        self.key = key
        self.lazy = lazy

    def __repr__(self):
        return f'<Backref <- {self.key}' + (' (lazy)' if self.lazy else '') + '>'


class Relationship:
    def __init__(self, name: str, model: 'core.Model', models: Dict[str, 'core.Model'],
                 model_name: str, backref: Optional[Backref], foreign_key: Optional[Column],
                 remote_side: Optional[Column], lazy: Union[bool, Literal['subquery']], secondary: Optional[str]):
        self.name = name
        self.model = model
        if model_name not in models:
            raise InitError(f'{model.__blnt__.name}.{name}: unknown "{model_name}" model')
        self.target_model = models[model_name]
        self.foreign_key = foreign_key
        self.remote_side = remote_side
        if secondary is not None and secondary not in models:
            raise InitError(f'{model.__blnt__.name}.{name}: unknown "{secondary}" model')
        self.secondary = models[secondary] if secondary is not None else None
        self.backref = backref
        self.lazy = lazy

    @property
    def model_name(self):
        return self.model.__blnt__.name

    @property
    def target_model_name(self):
        return self.target_model.__blnt__.name

    def __repr__(self):
        return (f'<Relationship {self.model_name}.{self.name} -> {self.target_model_name}'
                + ('  (lazy)' if self.lazy else '') + '>')
