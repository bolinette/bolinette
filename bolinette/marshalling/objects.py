class MarshallingObject:
    pass


class Field(MarshallingObject):
    def __init__(self, field_type, name, **kwargs):
        self.type = field_type
        self.name = name
        self.required = kwargs.get('required', False)
        self.function = kwargs.get('function')
        self.formatting = kwargs.get('formatting')

    def __repr__(self):
        return f'<MarshallingField {self.name}:{self.type}>'


class List(MarshallingObject):
    def __init__(self, name, element):
        self.name = name
        self.element = element

    def __repr__(self):
        return f'<MarshallingList {self.name}:[{repr(self.element)}]>'


class Definition(MarshallingObject):
    def __init__(self, name, model, key='default'):
        self.fields = []
        self.name = name
        self.key = f'{model}.{key}'

    def __repr__(self):
        return f'<MarshallingModel {self.key}>'
