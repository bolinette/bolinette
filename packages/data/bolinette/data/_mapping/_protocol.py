from collections.abc import Mapping
from typing import Any, get_args, get_origin, get_type_hints, override

import sqlalchemy as sa
from peritype import TWrap
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.orm import DeclarativeBase, Mapped

from bolinette.core.mapping import ABSENT, FieldSpec, Generation, Maybe, ObjectProtocol
from bolinette.core.mapping._utils import main_class


class SqlAlchemyProtocol(ObjectProtocol):
    priority = 100

    @override
    def matches(self, t: TWrap[Any]) -> bool:
        cls = main_class(t)
        return cls is not None and issubclass(cls, DeclarativeBase)

    @override
    def fields(self, t: TWrap[Any]) -> dict[str, FieldSpec]:
        cls = main_class(t)
        if cls is None or not issubclass(cls, DeclarativeBase):
            return {}
        insp = sa.inspect(cls)
        hints = get_type_hints(cls, include_extras=True)
        table = cls.__table__
        autoinc = getattr(table, "_autoincrement_column", None)

        specs: dict[str, FieldSpec] = {}
        for prop in insp.column_attrs:
            col = next(iter(prop.columns), None)
            if not isinstance(col, sa.Column):
                specs[prop.key] = self._spec(prop.key, hints, writable=False, has_default=True)
                continue
            server_side = (
                col is autoinc
                or col.identity is not None
                or col.computed is not None
                or col.server_default is not None
                or col.server_onupdate is not None
            )
            on_update = col.onupdate is not None or col.server_onupdate is not None
            if server_side:
                generation = Generation.SERVER_GENERATED
            elif col.default is not None:
                generation = Generation.CLIENT_DEFAULT
            else:
                generation = Generation.NONE
            specs[prop.key] = self._spec(
                prop.key,
                hints,
                nullable=bool(col.nullable),
                generation=generation,
                has_default=col.default is not None,
                writable=not server_side and not on_update,
                lazy=bool(prop.deferred),
            )

        for rel in insp.relationships:
            specs[rel.key] = self._spec(
                rel.key,
                hints,
                nullable=not rel.uselist,
                writable=False,
                has_default=True,
                lazy=True,
            )

        return specs

    @staticmethod
    def _spec(key: str, hints: dict[str, Any], **kwargs: Any) -> FieldSpec:
        anno = hints.get(key, Any)
        if get_origin(anno) is Mapped:
            anno = get_args(anno)[0]
        return FieldSpec.from_type(key, anno, **kwargs)

    @override
    def read_field(self, obj: Any, spec: FieldSpec) -> Maybe[Any]:
        try:
            state = sa.inspect(obj)
        except NoInspectionAvailable:
            state = None
        if state is not None and spec.key in state.unloaded:
            return ABSENT
        return getattr(obj, spec.key, ABSENT)

    @override
    def construct(self, t: TWrap[Any], values: Mapping[str, Any]) -> Any:
        cls = main_class(t)
        if cls is None:
            raise TypeError(f"{t} is not a declarative class")
        return cls(**values)

    @override
    def merge_collection(self, existing: Any, incoming: list[Any]) -> Any:
        if not isinstance(existing, list):
            return incoming
        existing[:] = incoming
        return existing  # pyright: ignore[reportUnknownVariableType]
