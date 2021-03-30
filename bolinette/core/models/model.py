from typing import List, Union, Tuple, Dict, Iterator, Literal

from bolinette import core, blnt
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
        # self.model_id: 'core.models.Column' = self._set_model_id()

    @property
    def model_id(self):
        attrs = filter(lambda col: col[1].model_id, self.get_columns())
        model_id = next(attrs)
        return model_id[1]

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

    def get_columns(self) -> Iterator[Tuple[str, 'core.models.Column']]:
        return self._get_attributes_of_type(self.parent, core.models.Column)

    def get_relationships(self) -> Iterator[Tuple[str, 'core.models.Relationship']]:
        return self._get_attributes_of_type(self.parent, core.models.Relationship)

    def get_properties(self) -> Iterator[Tuple[str, 'ModelProperty']]:
        return self._get_attributes_of_type(self.parent, ModelProperty)

    def get_back_refs(self) -> Iterator[Tuple[str, 'core.models.ColumnList']]:
        return self._get_attributes_of_type(self.parent, core.models.ColumnList)


class ModelProperty:
    def __init__(self, name, function):
        self.name = name
        self.function = function

    def __repr__(self):
        return f'<ModelProperty {self.name}>'
