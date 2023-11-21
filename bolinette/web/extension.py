from typing import override

from bolinette import core
from bolinette.core import Cache, command
from bolinette.core.extension import Extension
from bolinette.core.injection import injectable
from bolinette.web import WebResources
from bolinette.web.defaults.commands import run_server


class _WebExtension(Extension):
    def __init__(self) -> None:
        super().__init__("web", [core])

    @override
    def add_cached(self, cache: Cache) -> None:
        injectable(strategy="singleton", cache=cache)(WebResources)
        command("run server", "Runs the development server", cache=cache)(run_server)


web_ext = _WebExtension()
