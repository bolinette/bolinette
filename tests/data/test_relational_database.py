from sqlalchemy import Integer, String, select

from bolinette.ext.data.database import RelationalDatabase
from bolinette.ext.data.manager import (
    PrimaryKeyConstraint,
    TableColumn,
    TableDefinition,
)


async def test_create_simple_table() -> None:
    class TestEntity:
        id: int
        name: str

    rel_database = RelationalDatabase("sqlite+aiosqlite://", True)

    table_def = TableDefinition("test", TestEntity, "default")
    table_def.columns = {
        "id": TableColumn(table_def, "id", int, Integer, False, None),
        "name": TableColumn(table_def, "name", str, String, False, None),
    }
    table_def.constraints = {
        "test_pk": PrimaryKeyConstraint(table_def, "test_pk", [table_def.columns["id"]])
    }

    rel_database.init_tables({TestEntity: table_def})

    table: type[TestEntity] = rel_database._tables[TestEntity]  # type: ignore

    await rel_database.create_all()

    async with rel_database.create_session() as session:
        t1 = table(name="Test 1")
        t2 = table(name="Test 2")

        session.add(t1)
        session.add(t2)

        await session.commit()

    result = list((await session.execute(select(table))).scalars())
    assert len(result) == 2

    result = list((await session.execute(select(table).where(table.name == "Test 1"))).scalars())
    assert len(result) == 1

    await rel_database.dispose()
