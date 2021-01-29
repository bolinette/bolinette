from bolinette import blnt
from bolinette.decorators import command


@command('init_docs', 'Initialize the OpenAPI documentation')
async def init_docs(context: 'blnt.BolinetteContext'):
    context.docs.build()
