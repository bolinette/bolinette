from bolinette import abc
from bolinette.decorators import command


@command('init docs', 'Initialize the OpenAPI documentation', run_init=True)
async def init_docs(context: abc.Context):
    context.docs.build()
