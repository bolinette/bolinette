from bolinette.commands import command


@command('init_db')
async def init_db(context, *, run_seeders=True, **_):
    await context.db.drop_all()
    await context.db.create_all()
    if run_seeders:
        await context.db.run_seeders()
