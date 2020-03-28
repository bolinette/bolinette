import sqlalchemy


class DataType:
    def __init__(self, sql_alchemy_type):
        self.sql_alchemy_type = sql_alchemy_type

    def of_type(self, cls):
        return type(self) is cls

    def __repr__(self):
        return self.__class__.__name__

    def __str__(self):
        return self.__class__.__name__.lower()


class String(DataType):
    def __init__(self):
        super().__init__(sqlalchemy.String)


class Integer(DataType):
    def __init__(self):
        super().__init__(sqlalchemy.Integer)


class Float(DataType):
    def __init__(self):
        super().__init__(sqlalchemy.Float)


class Boolean(DataType):
    def __init__(self):
        super().__init__(sqlalchemy.Boolean)


class Date(DataType):
    def __init__(self):
        super().__init__(sqlalchemy.DateTime)


class Email(DataType):
    def __init__(self):
        super().__init__(sqlalchemy.String)


class Password(DataType):
    def __init__(self):
        super().__init__(sqlalchemy.String)


class ForeignKey(DataType):
    def __init__(self, model, key):
        super().__init__(sqlalchemy.ForeignKey)
        self.model = model
        self.key = key


class TypeClasses:
    DataType = DataType
    String = String
    Integer = Integer
    Float = Float
    Boolean = Boolean
    Date = Date
    Email = Email
    Password = Password
    ForeignKey = ForeignKey


class Types:
    @property
    def string(self):
        return String()

    @property
    def integer(self):
        return Integer()

    @property
    def float(self):
        return Float()

    @property
    def boolean(self):
        return Boolean()

    @property
    def date(self):
        return Date()

    @property
    def email(self):
        return Email()

    @property
    def password(self):
        return Password()

    def foreign_key(self, model, key):
        return ForeignKey(model, key)


types = Types()
