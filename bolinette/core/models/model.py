from typing import List, Union, Tuple, Dict, Optional, Type, Iterator

from bolinette import core, utils
from bolinette.blnt.database.engines import DatabaseEngine
from bolinette.exceptions import InitError

MappingPyTyping = List[Union['types.mapping.Column', 'types.mapping.Field',
                             'types.mapping.List', 'types.mapping.Definition']]
MappingListPyTyping = Union[MappingPyTyping, Tuple[str, MappingPyTyping]]


class Model:
    __blnt__: 'ModelMetadata' = None
    __mixins__: Dict[str, 'core.Mixin'] = {}

    def __init__(self, database: 'DatabaseEngine'):
        self.__props__ = ModelProps(self, database)

    @classmethod
    def payloads(cls) -> MappingListPyTyping:
        pass

    @classmethod
    def responses(cls) -> MappingListPyTyping:
        pass

    @classmethod
    def get_mixin(cls, name: str):
        return cls.__mixins__[name]

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

    def _get_cls_attribute_of_type(self, attr_type):
        return ((name, attribute)
                for name, attribute in vars(self.model.__class__).items()
                if isinstance(attribute, attr_type))

    def get_proxies(self, of_type: Optional[Type] = None) -> Iterator[Tuple[str, 'utils.InitProxy']]:
        proxies = self._get_cls_attribute_of_type(utils.InitProxy)
        if of_type is not None:
            return filter(lambda p: p[1].of_type(of_type), proxies)
        return proxies

    def _get_attribute_of_type(self, attr_type):
        return ((name, attribute)
                for name, attribute in vars(self.model).items()
                if isinstance(attribute, attr_type))

    def get_columns(self) -> Iterator[Tuple[str, 'core.models.Column']]:
        return self._get_attribute_of_type(core.models.Column)

    def get_relationships(self) -> Iterator[Tuple[str, 'core.models.Relationship']]:
        return self._get_attribute_of_type(core.models.Relationship)

    def get_properties(self) -> Iterator[Tuple[str, 'ModelProperty']]:
        return self._get_attribute_of_type(ModelProperty)


class ModelProperty:
    def __init__(self, name, function):
        self.name = name
        self.function = function

    def __repr__(self):
        return f'<ModelProperty {self.name}>'
