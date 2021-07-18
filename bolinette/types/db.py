import sqlalchemy as _sqlalchemy


class DataType:
    def __init__(self, name, sqlalchemy_type):
        self.name = name
        self.sqlalchemy_type = sqlalchemy_type

    def of_type(self, cls):
        return type(self) is cls

    def __repr__(self):
        return self.name


String = DataType('String', _sqlalchemy.String)
Integer = DataType('Integer', _sqlalchemy.Integer)
Float = DataType('Float', _sqlalchemy.Float)
Boolean = DataType('Boolean', _sqlalchemy.Boolean)
Date = DataType('Date', _sqlalchemy.DateTime)
Email = DataType('Email', _sqlalchemy.String)
Password = DataType('Password', _sqlalchemy.String)
