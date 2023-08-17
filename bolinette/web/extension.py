from typing_extensions import override

from bolinette import core
from bolinette.core import Cache, Extension


class _WebExtension(Extension):
    def __init__(self) -> None:
        super().__init__("web", [core])

    @override
    def add_cached(self, cache: Cache) -> None:
        pass


web_ext = _WebExtension()
