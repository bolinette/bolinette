from typing import Dict, List, Union, Tuple

from bolinette import db

MappingPyTyping = List[Union['mapping.Column', 'mapping.Field', 'mapping.List', 'mapping.Definition']]
MappingListPyTyping = Union[MappingPyTyping, Tuple[str, MappingPyTyping]]


class ModelMetadata:
    def __init__(self, name, model):
        self.name = name
        self.model = model
        self.orm_model = None
        self.orm_table = None
        self.orm_columns = {}

    def _get_attribute_of_type(self, attr_type):
        return dict([(name, attribute)
                     for name, attribute in vars(self.model.__class__).items()
                     if isinstance(attribute, attr_type)])

    def get_columns(self) -> Dict[str, 'db.defs.Column']:
        return self._get_attribute_of_type(db.defs.Column)

    def get_relationships(self) -> Dict[str, 'db.defs.Relationship']:
        return self._get_attribute_of_type(db.defs.Relationship)

    def get_properties(self) -> Dict[str, 'db.defs.ModelProperty']:
        return self._get_attribute_of_type(db.defs.ModelProperty)

    def new_entity(self, *args, **kwargs):
        return self.orm_model(*args, **kwargs)


class Model:
    def __init__(self, name):
        self.__blnt__ = ModelMetadata(name, self)

    @classmethod
    def payloads(cls) -> MappingListPyTyping:
        pass

    @classmethod
    def responses(cls) -> MappingListPyTyping:
        pass

    def query(self):
        return db.engine.session.query(self.__blnt__.orm_model)
