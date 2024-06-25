from typing import override

from bolinette import core
from bolinette.core import Cache
from bolinette.core.extension import Extension


class ApiExtension(Extension):
    def __init__(self) -> None:
        super().__init__("web", [core])

    @override
    def add_cached(self, cache: Cache) -> None: ...


api_ext = ApiExtension()
