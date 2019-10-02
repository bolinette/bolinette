class MarshallingType:
    def __repr__(self):
        return self.__class__.__name__


class String(MarshallingType):
    pass


class Integer(MarshallingType):
    pass


class Float(MarshallingType):
    pass


class Boolean(MarshallingType):
    pass


class Date(MarshallingType):
    pass


class Email(MarshallingType):
    pass


class Password(MarshallingType):
    pass


class ForeignKey(MarshallingType):
    def __init__(self, model, key):
        self.model = model
        self.key = key


class TypesClasses:
    String = String
    Integer = Integer
    Float = Float
    Boolean = Boolean
    Date = Date
    Email = Email
    Password = Password
    ForeignKey = ForeignKey


class Types:
    classes = TypesClasses

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
