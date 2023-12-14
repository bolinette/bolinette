from bolinette.data.relational import EntityManager


async def create_db_tables(entities: EntityManager):
    await entities.create_all()
