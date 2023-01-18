from typing import Annotated

from sqlalchemy import Integer, String, Table

from bolinette.ext.data import Entity, PrimaryKey
from bolinette.ext.data.database import RelationalDatabase
from bolinette.ext.data.manager import (
    PrimaryKeyConstraint,
    TableColumn,
    TableDefinition,
)


async def test_create_simple_table() -> None:
    class TestEntity(Entity):
        id: Annotated[int, PrimaryKey()]
        name: str

    rel_database = RelationalDatabase("default", "sqlite+aiosqlite://", True)

    table_def = TableDefinition("test", TestEntity, "default")
    table_def.columns = {
        "id": TableColumn(table_def, "id", int, Integer, False, None),
        "name": TableColumn(table_def, "name", str, String, False, None),
    }
    table_def.constraints = {
        "test_pk": PrimaryKeyConstraint(table_def, "test_pk", [table_def.columns["id"]])
    }

    rel_database.init_tables({TestEntity: table_def})

    sql_def = rel_database._sql_defs[TestEntity]

    assert hasattr(sql_def, '__table__')

    orm_table = getattr(sql_def, '__table__')
    assert isinstance(orm_table, Table)

    assert len(orm_table.columns) == 2
    assert 'id' in orm_table.columns
    assert 'name' in orm_table.columns

    id_col = orm_table.columns['id']
    assert id_col.name == 'id'
    assert id_col.primary_key is True
    assert isinstance(id_col.type, Integer)

    name_col = orm_table.columns['name']
    assert name_col.name == 'name'
    assert name_col.primary_key is False
    assert isinstance(name_col.type, String)
