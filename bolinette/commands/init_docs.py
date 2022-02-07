from bolinette import web
from bolinette.core import BolinetteContext
from bolinette.decorators import command


@command("init docs", "Initialize the OpenAPI documentation", exts=[web.ext])
async def init_docs(context: BolinetteContext):
    context.docs.build()
