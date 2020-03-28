from bolinette import db
from bolinette.commands import command


@command('init_db')
async def init_db(*, run_seeders=False, **_):
    await db.engine.drop_all()
    await db.engine.create_all()
    if run_seeders:
        await db.engine.run_seeders()
