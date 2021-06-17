from typing import List, Union, Tuple, Dict, Iterator, Literal

from bolinette import core, blnt
from bolinette.blnt.database.engines import DatabaseEngine

MappingPyTyping = List[Union['types.mapping.Column', 'types.mapping.Field',
                             'types.mapping.List', 'types.mapping.Definition']]
MappingListPyTyping = Union[MappingPyTyping, Tuple[str, MappingPyTyping]]


class Model:
    __blnt__: 'ModelMetadata' = None

    def __init__(self, database: 'DatabaseEngine'):
        self.__props__ = ModelProps(self, database)

    def payloads(self) -> MappingListPyTyping:
        pass

    def responses(self) -> MappingListPyTyping:
        pass

    def get_mixin(self, name: str):
        return self.__props__.mixins[name]

    def __repr__(self):
        return f'<Model {self.__blnt__.name}>'


class ModelMetadata:
    def __init__(self, name: str, database: str, relational: bool, join: bool, mixins: List[str],
                 merge_defs: Literal['ignore', 'append', 'overwrite']):
        self.name = name
        self.database = database
        self.relational = relational
        self.join = join
        self.mixins = mixins
        self.merge_defs = merge_defs


class ModelProps(blnt.Properties):
    def __init__(self, model: Model, database: 'DatabaseEngine'):
        super().__init__(model)
        self.model = model
        self.database = database
        self.mixins: Dict[str, core.Mixin] = {}
        self.primary: Union['core.models.Column', List['core.models.Column'], None] = None
        self.model_id: Union['core.models.Column', List['core.models.Column'], None] = None

    def get_columns(self) -> Iterator[Tuple[str, 'core.models.Column']]:
        return self._get_attributes_of_type(self.parent, core.models.Column)

    def get_relationships(self) -> Iterator[Tuple[str, 'core.models.Relationship']]:
        return self._get_attributes_of_type(self.parent, core.models.Relationship)

    def get_properties(self) -> Iterator[Tuple[str, 'ModelProperty']]:
        return self._get_cls_attributes_of_type(type(self.parent), ModelProperty)

    def get_back_refs(self) -> Iterator[Tuple[str, 'core.models.ColumnList']]:
        return self._get_attributes_of_type(self.parent, core.models.ColumnList)


class ModelProperty:
    def __init__(self, name, function):
        self.name = name
        self.function = function

    def __repr__(self):
        return f'<ModelProperty {self.name}>'
