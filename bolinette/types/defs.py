from typing import Any, Literal

from bolinette import types, data, core


class Reference(core.InstantiableAttribute["core.models.Reference"]):
    def __init__(self, model_name: str, column_name: str) -> None:
        super().__init__(
            data.models.Reference, dict(model_name=model_name, column_name=column_name)
        )


class Column(core.InstantiableAttribute["core.models.Column"]):
    def __init__(
        self,
        data_type: "types.db.DataType",
        *,
        reference: Reference | None = None,
        primary_key: bool = False,
        auto: bool | None = None,
        nullable: bool = True,
        unique: bool = False,
        entity_key: bool = False,
        default: Any | None = None
    ) -> None:
        super().__init__(
            data.models.Column,
            dict(
                data_type=data_type,
                reference=reference,
                primary_key=primary_key,
                auto=auto,
                nullable=nullable,
                unique=unique,
                entity_key=entity_key,
                default=default,
            ),
        )


class Backref(core.InstantiableAttribute["core.models.Backref"]):
    def __init__(self, key: str, *, lazy: bool = True) -> None:
        super().__init__(data.models.Backref, dict(key=key, lazy=lazy))


class Relationship(core.InstantiableAttribute["core.models.Relationship"]):
    def __init__(
        self,
        model_name: str,
        *,
        backref: Backref = None,
        foreign_key: str | None = None,
        lazy: bool | Literal["subquery"] = False,
        secondary: str = None,
        remote_side: str | None = None
    ) -> None:
        super().__init__(
            data.models.Relationship,
            dict(
                model_name=model_name,
                backref=backref,
                foreign_key=foreign_key,
                lazy=lazy,
                secondary=secondary,
                remote_side=remote_side,
            ),
        )
