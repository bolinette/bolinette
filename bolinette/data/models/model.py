from collections.abc import Iterator, Iterable
from typing import Literal, Any

from bolinette import abc, data, core, mapping


class Model(abc.WithContext, abc.core.Model):
    __blnt__: 'ModelMetadata' = None  # type: ignore

    def __init__(self, context: abc.Context):
        super().__init__(context)
        self.__props__ = ModelProps(self, context.db.get_engine(self.__blnt__.database))

    def payloads(self) -> Iterable[tuple[str, list[mapping.MappingObject]] | list[mapping.MappingObject]]:
        pass

    def responses(self) -> Iterable[tuple[str, list[mapping.MappingObject]] | list[mapping.MappingObject]]:
        pass

    def get_mixin(self, name: str):
        return self.__props__.mixins[name]

    def __repr__(self):
        return f'<Model {self.__blnt__.name}>'


class ModelMetadata:
    def __init__(self, name: str, database: str, relational: bool, join: bool, mixins: list[str],
                 merge_defs: Literal['ignore', 'append', 'overwrite']):
        self.name = name
        self.database = database
        self.relational = relational
        self.join = join
        self.mixins = mixins
        self.merge_defs = merge_defs


class ModelProps(core.Properties):
    def __init__(self, model: Model, database: abc.db.Engine):
        super().__init__(model)
        self.model = model
        self.database = database
        self.repo: data.Repository | None = None
        self.mixins: dict[str, data.Mixin] = {}
        self.primary: list['data.models.Column'] | None = None
        self.entity_key: list['data.models.Column'] | None = None

    def get_columns(self) -> Iterator[tuple[str, 'data.models.Column']]:
        return self._get_attributes_of_type(self.parent, data.models.Column)

    def get_relationships(self) -> Iterator[tuple[str, 'data.models.Relationship']]:
        return self._get_attributes_of_type(self.parent, data.models.Relationship)

    def get_properties(self) -> Iterator[tuple[str, 'ModelProperty']]:
        return self._get_cls_attributes_of_type(type(self.parent), ModelProperty)

    def get_back_refs(self) -> Iterator[tuple[str, 'data.models.ColumnList']]:
        return self._get_attributes_of_type(self.parent, data.models.ColumnList)


class ModelProperty:
    def __init__(self, name, function):
        self.name = name
        self.function = function

    def __repr__(self):
        return f'<ModelProperty {self.name}>'
