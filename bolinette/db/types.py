from typing import Union, Dict, List, Tuple

import sqlalchemy

from bolinette import db


class DataType:
    def __init__(self, name, sqlalchemy_type):
        self.name = name
        self.sqlalchemy_type = sqlalchemy_type

    def of_type(self, cls):
        return type(self) is cls

    def __repr__(self):
        return self.name


String = DataType('String', sqlalchemy.String)
Integer = DataType('Integer', sqlalchemy.Integer)
Float = DataType('Float', sqlalchemy.Float)
Boolean = DataType('Boolean', sqlalchemy.Boolean)
Date = DataType('Date', sqlalchemy.DateTime)
Email = DataType('Email', sqlalchemy.String)
Password = DataType('Password', sqlalchemy.String)

MappingPyTyping = List[Union['mapping.Column', 'mapping.Field', 'mapping.List', 'mapping.Definition']]
MappingListPyTyping = Union[MappingPyTyping, Tuple[str, MappingPyTyping]]


class Model:
    __orm_model__ = None
    __model_name__ = None

    @classmethod
    def payloads(cls) -> MappingListPyTyping:
        pass

    @classmethod
    def responses(cls) -> MappingListPyTyping:
        pass

    @classmethod
    def get_columns(cls) -> Dict[str, 'Column']:
        columns = dict([(name, attribute) for name, attribute in vars(cls).items() if isinstance(attribute, Column)])
        for base in [base for base in cls.__bases__ if issubclass(base, Model) and base is not Model]:
            columns.update(base.get_columns())
        return columns

    @classmethod
    def get_relationships(cls) -> Dict[str, 'Relationship']:
        relationships = dict([(name, attribute) for name, attribute in vars(cls).items()
                              if isinstance(attribute, Relationship)])
        for base in [base for base in cls.__bases__ if issubclass(base, Model) and base is not Model]:
            relationships.update(base.get_relationships())
        return relationships

    @classmethod
    def query(cls):
        return db.engine.session.query(cls.__orm_model__)

    def __new__(cls, *args, **kwargs):
        return cls.__orm_model__(*args, **kwargs)


class Reference:
    def __init__(self, model_name: str, column_name: str):
        self.model_name = model_name
        self.column_name = column_name

    def __repr__(self):
        return f'<Reference -> {self.model_name}.{self.column_name}'


class Column:
    def __init__(self, data_type: DataType, *, reference: Reference = None, primary_key: bool = False,
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
