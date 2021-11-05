from typing import Literal, Any, Optional

from bolinette import abc, types, core


class Reference(abc.inject.Instantiable):
    def __init__(self, model: 'core.Model', column: 'core.models.Column',
                 target_model: 'core.Model', target_column: 'core.models.Column'):
        self._model = model
        self._column = column
        self._target_model = target_model
        self._target_column = target_column

    @property
    def model_name(self):
        return self._model.__blnt__.name

    @property
    def column_name(self):
        return self._column.name

    @property
    def target_model_name(self):
        return self._target_model.__blnt__.name

    @property
    def target_column_name(self):
        return self._target_column.name

    @property
    def target_path(self):
        return f'{self.target_model_name}.{self.target_column_name}'

    def __repr__(self):
        return f'<Reference {self.model_name}.{self.column_name} -> {self.target_path}>'


class Column(abc.inject.Instantiable):
    def __init__(self, name: str, model: 'core.Model', data_type: 'types.db.DataType',
                 reference: Reference | None, primary_key: bool, auto: bool | None,
                 nullable: bool, unique: bool, entity_key: bool, default: Any | None):
        self._name = name
        self._type = data_type
        self._model = model
        self._auto_increment = auto
        self._reference = reference
        self._primary_key = primary_key
        self._nullable = nullable
        self._unique = unique
        self._entity_key = entity_key
        self._default = default

    @property
    def name(self):
        return self._name

    @property
    def model_name(self):
        return self._model.__blnt__.name

    @property
    def primary_key(self):
        return self._primary_key

    @property
    def auto_increment(self):
        return self._auto_increment

    @auto_increment.setter
    def auto_increment(self, value: bool):
        self._auto_increment = value

    @property
    def entity_key(self):
        return self._entity_key

    @property
    def reference(self):
        return self._reference

    @reference.setter
    def reference(self, value: Reference):
        self._reference = value

    @property
    def type(self):
        return self._type

    @property
    def default(self):
        return self._default

    @property
    def unique(self):
        return self._unique

    @property
    def nullable(self):
        return self._nullable

    @nullable.setter
    def nullable(self, value: bool):
        self._nullable = value

    def __repr__(self):
        s = f'<Column {self.model_name}.{self._name}: {repr(self._type)}'
        if self._reference is not None:
            s += f' -> {self._reference.target_path}'
        return s + '>'


class ColumnList:
    def __init__(self, name: str, model: 'core.Model', origin: 'core.Model'):
        self._name = name
        self._model = model
        self._origin = origin


class Backref:
    def __init__(self, model: 'core.Model', relationship: 'core.models.Relationship',
                 key: str, lazy: bool):
        self._model = model
        self._relationship = relationship
        self._key = key
        self._lazy = lazy

    @property
    def key(self):
        return self._key

    @property
    def lazy(self):
        return self._lazy

    def __repr__(self):
        return f'<Backref <- {self._key}' + (' (lazy)' if self._lazy else '') + '>'


class Relationship(abc.inject.Instantiable):
    def __init__(self, name: str, model: 'core.Model', target_model: 'core.Model', backref: Backref | None,
                 foreign_key: Column | None, remote_side: Column | None, lazy: bool | Literal['subquery'],
                 secondary: Optional['core.Model']):
        self._name = name
        self._model = model
        self._target_model = target_model
        self._foreign_key = foreign_key
        self._remote_side = remote_side
        self._secondary = secondary
        self._backref = backref
        self._lazy = lazy

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def backref(self):
        return self._backref

    @backref.setter
    def backref(self, value: Backref):
        self._backref = value

    @property
    def foreign_key(self):
        return self._foreign_key

    @foreign_key.setter
    def foreign_key(self, value: Column):
        self._foreign_key = value

    @property
    def remote_side(self):
        return self._remote_side

    @remote_side.setter
    def remote_side(self, value: Column):
        self._remote_side = value

    @property
    def target_model(self):
        return self._target_model

    @property
    def secondary(self):
        return self._secondary

    @property
    def lazy(self):
        return self._lazy

    @property
    def target_model_name(self):
        return self._target_model.__blnt__.name

    def __repr__(self):
        return (f'<Relationship {self._model.__blnt__.name}.{self._name} -> {self.target_model_name}'
                + ('  (lazy)' if self._lazy else '') + '>')
