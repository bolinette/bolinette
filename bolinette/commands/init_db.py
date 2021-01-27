from bolinette import blnt
from bolinette.decorators import command


@command('init_db')
async def init_db(context: 'blnt.BolinetteContext'):
    await context.db.drop_all()
    await context.db.create_all()
    await context.db.run_seeders(context)
