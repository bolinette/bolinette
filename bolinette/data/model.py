from typing import Dict, List, Union, Tuple

from bolinette import types

MappingPyTyping = List[Union['mapping.Column', 'mapping.Field', 'mapping.List', 'mapping.Definition']]
MappingListPyTyping = Union[MappingPyTyping, Tuple[str, MappingPyTyping]]


class ModelMetadata:
    def __init__(self, name, model):
        self.name = name
        self.model = model

    def _get_attribute_of_type(self, attr_type):
        return dict([(name, attribute)
                     for name, attribute in vars(self.model.__class__).items()
                     if isinstance(attribute, attr_type)])

    def get_columns(self) -> Dict[str, 'types.Column']:
        return self._get_attribute_of_type(types.Column)

    def get_relationships(self) -> Dict[str, 'types.Relationship']:
        return self._get_attribute_of_type(types.Relationship)

    def get_properties(self) -> Dict[str, 'types.ModelProperty']:
        return self._get_attribute_of_type(types.ModelProperty)


class Model:
    def __init__(self, name):
        self.__blnt__ = ModelMetadata(name, self)

    @classmethod
    def payloads(cls) -> MappingListPyTyping:
        pass

    @classmethod
    def responses(cls) -> MappingListPyTyping:
        pass

    def __repr__(self):
        return f'<Model {self.__blnt__.name}>'
