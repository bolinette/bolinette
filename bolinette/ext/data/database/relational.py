from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from bolinette.ext.data import Entity
from bolinette.ext.data.manager import PrimaryKeyConstraint, TableDefinition, UniqueConstraint


class RelationalDatabase:
    def __init__(self, uri: str, echo: bool):
        self._engine = create_async_engine(uri, echo=echo)
        self._session_maker = async_sessionmaker(self._engine)
        self._declarative_base: type[DeclarativeBase] = type(
            "RelationalBase", (DeclarativeBase,), {}
        )
        self._tables: dict[type[Entity], type[DeclarativeBase]] = {}

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
                *mapped_cols[entity].values()
            )
            sql_tables[entity] = sql_table

        for table_name, sql_table in sql_tables.items():
            model_defs: dict[str, Any] = {}
            model_defs["__table__"] = sql_tables[table_name]

            table_def = table_defs[table_name]
            for const_name, constraint in table_def.constraints.items():
                const_cols = [
                    mapped_cols[table_name][col.name] for col in constraint.columns
                ]
                if isinstance(constraint, PrimaryKeyConstraint):
                    model_defs[const_name] = sa.PrimaryKeyConstraint(*const_cols, name=const_name)
                if isinstance(constraint, UniqueConstraint):
                    model_defs[const_name] = sa.UniqueConstraint(*const_cols, name=const_name)

            sql_model = type(table_def.name, (self._declarative_base,), model_defs)
            self._tables[table_def.entity] = sql_model

    async def create_all(self) -> None:
        async with self._engine.begin() as connection:
            await connection.run_sync(self._declarative_base.metadata.create_all)

    async def dispose(self) -> None:
        await self._engine.dispose()
