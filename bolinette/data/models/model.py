from abc import ABC
from collections.abc import Iterator, Iterable
from typing import Generic, Literal, TypeVar

from bolinette import data
from bolinette.core import abc, BolinetteContext, Properties
from bolinette.data import mapping, DataContext, WithDataContext
from bolinette.data.database.engines import AbstractEngine


class Entity(ABC):
    ...


T_Entity = TypeVar("T_Entity", bound=Entity)


class Model(abc.WithContext, WithDataContext, Generic[T_Entity]):
    __blnt__: "ModelMetadata" = None  # type: ignore

    def __init__(self, context: BolinetteContext, data_ctx: DataContext):
        abc.WithContext.__init__(self, context)
        WithDataContext.__init__(self, data_ctx)
        self.__props__ = ModelProps(
            self, self.data_ctx.db.get_engine(self.__blnt__.database)
        )

    def payloads(
        self,
    ) -> Iterable[
        tuple[str, list[mapping.MappingObject]] | list[mapping.MappingObject]
    ]:
        ...

    def responses(
        self,
    ) -> Iterable[
        tuple[str, list[mapping.MappingObject]] | list[mapping.MappingObject]
    ]:
        ...

    def get_mixin(self, name: str):
        return self.__props__.mixins[name]

    def __repr__(self):
        return f"<Model {self.__blnt__.name}>"


class ModelMetadata:
    def __init__(
        self,
        name: str,
        database: str,
        relational: bool,
        join: bool,
        mixins: list[str],
        merge_defs: Literal["ignore", "append", "overwrite"],
    ):
        self.name = name
        self.database = database
        self.relational = relational
        self.join = join
        self.mixins = mixins
        self.merge_defs = merge_defs


class ModelProps(Properties, Generic[T_Entity]):
    def __init__(self, model: Model[T_Entity], database: AbstractEngine):
        super().__init__(model)
        self.model = model
        self.database = database
        self.repo: data.Repository[T_Entity] | None = None
        self.mixins: dict[str, data.Mixin] = {}
        self.primary: list["data.models.Column"] | None = None
        self.entity_key: list["data.models.Column"] | None = None

    def get_columns(self) -> Iterator[tuple[str, "data.models.Column"]]:
        return self._get_attributes_of_type(self.parent, data.models.Column)

    def get_relationships(self) -> Iterator[tuple[str, "data.models.Relationship"]]:
        return self._get_attributes_of_type(self.parent, data.models.Relationship)

    def get_properties(self) -> Iterator[tuple[str, "ModelProperty"]]:
        return self._get_cls_attributes_of_type(type(self.parent), ModelProperty)

    def get_back_refs(self) -> Iterator[tuple[str, "data.models.ColumnList"]]:
        return self._get_attributes_of_type(self.parent, data.models.ColumnList)


class ModelProperty:
    def __init__(self, name, function):
        self.name = name
        self.function = function

    def __repr__(self):
        return f"<ModelProperty {self.name}>"
