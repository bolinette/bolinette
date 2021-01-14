from typing import List, Union, Tuple, Any, Generator

from bolinette import types
from bolinette.blnt.database.engines import DatabaseEngine
from bolinette.exceptions import InitError

MappingPyTyping = List[Union['types.mapping.Column', 'types.mapping.Field',
                             'types.mapping.List', 'types.mapping.Definition']]
MappingListPyTyping = Union[MappingPyTyping, Tuple[str, MappingPyTyping]]


class Model:
    __blnt__: 'ModelMetadata' = None

    def __init__(self, database: 'DatabaseEngine'):
        self.__props__ = ModelProps(self, database)

    @classmethod
    def payloads(cls) -> MappingListPyTyping:
        pass

    @classmethod
    def responses(cls) -> MappingListPyTyping:
        pass

    def __repr__(self):
        return f'<Model {self.__blnt__.name}>'


class ModelMetadata:
    def __init__(self, name: str, database: str, relational: bool, join: bool):
        self.name = name
        self.database = database
        self.relational = relational
        self.join = join


class ModelProps:
    def __init__(self, model: Model, database: 'DatabaseEngine'):
        self.model = model
        self.database = database
        self.model_id: 'types.defs.Column' = self._set_model_id()

    def _set_model_id(self):
        model_id = None
        if self.model.__blnt__.join:
            return model_id
        for col_name, column in self.get_columns():
            if column.model_id and model_id is not None:
                raise InitError(f'Model "{self.model.__blnt__.name}" already has a model id')
            if column.model_id:
                model_id = column
        if model_id is None:
            raise InitError(f'Model "{self.model.__blnt__.name}" has no column marked as model id')
        if not model_id.unique and not model_id.primary_key:
            raise InitError(f'Model "{self.model.__blnt__.name}"\'s model id should be either '
                            'a unique column or a primary key')
        return model_id

    def _get_attribute_of_type(self, attr_type):
        return ((name, attribute)
                for name, attribute in vars(self.model.__class__).items()
                if isinstance(attribute, attr_type))

    def get_columns(self) -> Generator[Tuple[str, 'types.defs.Column'], Any, None]:
        return self._get_attribute_of_type(types.defs.Column)

    def get_relationships(self) -> Generator[Tuple[str, 'types.defs.Relationship'], Any, None]:
        return self._get_attribute_of_type(types.defs.Relationship)

    def get_properties(self) -> Generator[Tuple[str, 'ModelProperty'], Any, None]:
        return self._get_attribute_of_type(ModelProperty)


class ModelProperty:
    def __init__(self, name, function):
        self.name = name
        self.function = function

    def __repr__(self):
        return f'<ModelProperty {self.name}>'
