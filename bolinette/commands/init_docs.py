from bolinette import blnt
from bolinette.commands import command


@command('init_docs')
async def init_docs(context: 'blnt.BolinetteContext'):
    context.docs.build()
