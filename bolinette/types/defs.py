from typing import Union, Dict

from bolinette import types


class ModelProperty:
    def __init__(self, name, function):
        self.name = name
        self.function = function

    def __repr__(self):
        return f'<ModelProperty {self.name}>'


class Reference:
    def __init__(self, model_name: str, column_name: str):
        self.model_name = model_name
        self.column_name = column_name

    def __repr__(self):
        return f'<Reference -> {self.model_name}.{self.column_name}'


class Column:
    def __init__(self, data_type: 'types.types.DataType', *, reference: Reference = None, primary_key: bool = False,
                 nullable: bool = True, unique: bool = False):
        self.type = data_type
        self.reference = reference
        self.primary_key = primary_key
        self.nullable = nullable
        self.unique = unique
        self.name = None
        self.model = None
        self.orm_def = None

    def __repr__(self):
        return f'<Column {self.name}: {repr(self.type)}>'

    def __eq__(self, other):
        return self.orm_def == other

    def __ne__(self, other):
        return self.orm_def != other

    def __le__(self, other):
        return self.orm_def <= other

    def __lt__(self, other):
        return self.orm_def < other

    def __ge__(self, other):
        return self.orm_def >= other

    def __gt__(self, other):
        return self.orm_def > other


class Backref:
    def __init__(self, key: str, *, lazy: bool = True):
        self.key = key
        self.lazy = lazy

    def __repr__(self):
        return f'<Backref <- {self.key}' + (' lazy ' if self.lazy else '') + '>'


class Relationship:
    def __init__(self, model_name: str, *, backref: Backref = None, foreign_key: Column = None,
                 lazy: Union[bool, str] = False, secondary: str = None):
        self.model_name = model_name
        self.foreign_key = foreign_key
        self.backref = backref
        self.secondary = secondary
        self.lazy = lazy
        self.name = None
        self.model = None
        self.orm_def = None

    def __repr__(self):
        return f'<Relationship {self.name} -> {self.model_name}' + (' lazy ' if self.lazy else '') + '>'
