from typing import Any, TypeVar

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from bolinette.ext.data import Entity
from bolinette.ext.data.manager import (
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    TableDefinition,
    TableReference,
    UniqueConstraint,
)
from bolinette.utils import StringUtils

EntityT = TypeVar("EntityT", bound=Entity)


class RelationalDatabase:
    def __init__(self, name: str, uri: str, echo: bool):
        self._engine = create_async_engine(uri, echo=echo)
        self._session_maker = async_sessionmaker(self._engine)
        self._declarative_base: type[DeclarativeBase] = type(
            f"{StringUtils.capitalize(name)}Database", (DeclarativeBase,), {}
        )
        self._sql_defs: dict[type[Entity], type[DeclarativeBase]] = {}

    def get_definition(self, entity: type[EntityT]) -> type[Any]:
        return self._sql_defs[entity]

    def create_session(self) -> AsyncSession:
        return self._session_maker()

    def init_tables(self, table_defs: dict[type[Entity], TableDefinition]) -> None:
        mapped_cols: dict[type[Entity], dict[str, sa.Column]] = {}
        sql_tables: dict[type[Entity], sa.Table] = {}

        for entity, table_def in table_defs.items():
            mapped_cols[entity] = {}
            for col_name, column in table_def.columns.items():
                sql_column: sa.Column = sa.Column(
                    col_name, column.sql_type, nullable=column.nullable
                )
                mapped_cols[entity][col_name] = sql_column
            sql_table = sa.Table(
                table_def.name,
                self._declarative_base.metadata,
                *mapped_cols[entity].values(),
            )
            sql_tables[entity] = sql_table

        for entity, sql_table in sql_tables.items():
            model_defs: dict[str, Any] = {}
            model_defs["__table__"] = sql_tables[entity]

            table_def = table_defs[entity]
            for const_name, constraint in table_def.constraints.items():
                const_cols = [
                    mapped_cols[entity][col.name] for col in constraint.columns
                ]
                if isinstance(constraint, PrimaryKeyConstraint):
                    model_defs[const_name] = sa.PrimaryKeyConstraint(
                        *const_cols, name=const_name
                    )
                if isinstance(constraint, UniqueConstraint):
                    model_defs[const_name] = sa.UniqueConstraint(
                        *const_cols, name=const_name
                    )
                if isinstance(constraint, ForeignKeyConstraint):
                    target_cols = [
                        mapped_cols[constraint.target.entity][col.name]
                        for col in constraint.target_columns
                    ]
                    model_defs[const_name] = sa.ForeignKeyConstraint(
                        const_cols, target_cols, name=const_name
                    )
            for ref_name, reference in table_def.references.items():
                if isinstance(reference, TableReference):
                    model_defs[ref_name] = relationship(
                        reference.target.name,
                        foreign_keys=model_defs[reference.constraint.name],
                        lazy="raise_on_sql",
                    )

            sql_model = type(table_def.name, (self._declarative_base,), model_defs)
            self._sql_defs[table_def.entity] = sql_model

    async def create_all(self) -> None:
        async with self._engine.begin() as connection:
            await connection.run_sync(self._declarative_base.metadata.create_all)

    async def dispose(self) -> None:
        await self._engine.dispose()
