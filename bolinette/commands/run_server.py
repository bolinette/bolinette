import bolinette
from bolinette import web
from bolinette.core import BolinetteContext
from bolinette.decorators import command


@command("run server", "Run the internal server", exts=[web.ext])
@command.argument(
    "option", "host", flag="H", summary="The host the server will listen to"
)
@command.argument(
    "option",
    "port",
    flag="p",
    summary="The port the server will listen on",
    value_type=int,
)
def run_server(context: BolinetteContext, host: str = None, port: int = None):
    context.registry.get(bolinette.Bolinette).start_server(host=host, port=port)
