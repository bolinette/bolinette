class MappingObject:
    pass


class Field(MappingObject):
    def __init__(self, field_type, *, key=None, name=None,
                 default=None, required=False, function=None, formatting=None):
        self.type = field_type
        self.key = key
        self.name = name
        self.required = required
        self.default = default
        self.function = function
        self.formatting = formatting
        if not self.name and self.key:
            self.name = self.key

    def __repr__(self):
        return f'<MappingField {self.key}:{self.type} -> {self.name}>'


class List(MappingObject):
    def __init__(self, name, element):
        self.name = name
        self.element = element

    def __repr__(self):
        return f'<MappingList {self.name}:[{repr(self.element)}]>'


class Definition(MappingObject):
    def __init__(self, model_name, model_key='default', *, key=None, name=None, function=None):
        self.fields = []
        self.key = key
        self.name = name
        self.function = function
        self.model_key = f'{model_name}.{model_key}'
        if not self.name and self.key:
            self.name = self.key

    def __repr__(self):
        return f'<MappingModel {self.model_key}>'
