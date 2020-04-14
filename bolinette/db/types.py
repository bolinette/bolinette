import sqlalchemy


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
