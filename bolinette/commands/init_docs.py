from bolinette import blnt
from bolinette.decorators import command


@command('init docs', 'Initialize the OpenAPI documentation', run_init=True)
async def init_docs(context: 'blnt.BolinetteContext'):
    context.docs.build()
