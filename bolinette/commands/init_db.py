from bolinette import core, data
from bolinette.decorators import command


@command("init db", "Initialize the database", exts=[data.ext])
@command.argument(
    "flag", "seeders", flag="s", summary="Run the seeders after database creation"
)
async def init_db(context: core.BolinetteContext, seeders: bool):
    data_ctx = context.registry.get(data.DataContext)
    context.logger.info("==== Initializing database ====")
    context.logger.info("**** Dropping all tables")
    await data_ctx.db.drop_all()
    context.logger.info("**** Creating all tables")
    await data_ctx.db.create_all()
    if seeders:
        context.logger.info("**** Running seeders")
        await data_ctx.db.run_seeders(log=True, tab=5)
    context.logger.info("==== Done ====")
