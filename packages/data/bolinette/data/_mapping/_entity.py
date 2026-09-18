import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase

from bolinette.data.exceptions import ColumnNotNullableError, DataError, EntityValidationError


def validate_entity(entity: DeclarativeBase) -> None:
    cls = type(entity)
    insp = sa.inspect(cls)
    table = cls.__table__
    autoinc = getattr(table, "_autoincrement_column", None)
    errors: list[DataError] = []
    for prop in insp.column_attrs:
        col = next(iter(prop.columns), None)
        if not isinstance(col, sa.Column) or col.nullable:
            continue
        if (
            col is autoinc
            or col.identity is not None
            or col.computed is not None
            or col.server_default is not None
            or col.default is not None
            or col.onupdate is not None
        ):
            continue
        if getattr(entity, prop.key, None) is None:
            errors.append(ColumnNotNullableError(cls, prop.key))
    if errors:
        raise EntityValidationError(cls, errors)
