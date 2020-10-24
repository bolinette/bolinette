from typing import Dict, List, Union, Tuple

from bolinette import types

MappingPyTyping = List[Union['types.mapping.Column', 'types.mapping.Field',
                             'types.mapping.List', 'types.mapping.Definition']]
MappingListPyTyping = Union[MappingPyTyping, Tuple[str, MappingPyTyping]]


class Model:
    __blnt__: 'ModelMetadata' = None

    def __init__(self):
        self.__props__ = ModelProps(self)

    @classmethod
    def payloads(cls) -> MappingListPyTyping:
        pass

    @classmethod
    def responses(cls) -> MappingListPyTyping:
        pass

    def __repr__(self):
        return f'<Model {self.__blnt__.name}>'


class ModelMetadata:
    def __init__(self, name):
        self.name = name


class ModelProps:
    def __init__(self, model):
        self.model = model

    def _get_attribute_of_type(self, attr_type):
        return dict([(name, attribute)
                     for name, attribute in vars(self.model.__class__).items()
                     if isinstance(attribute, attr_type)])

    def get_columns(self) -> Dict[str, 'types.defs.Column']:
        return self._get_attribute_of_type(types.defs.Column)

    def get_relationships(self) -> Dict[str, 'types.defs.Relationship']:
        return self._get_attribute_of_type(types.defs.Relationship)

    def get_properties(self) -> Dict[str, 'ModelProperty']:
        return self._get_attribute_of_type(ModelProperty)


class ModelProperty:
    def __init__(self, name, function):
        self.name = name
        self.function = function

    def __repr__(self):
        return f'<ModelProperty {self.name}>'
