from bolinette.core import environment
from bolinette.data import __data_cache__


class _DatabaseSection:
    name: str
    url: str


@environment("data", cache=__data_cache__)
class DataSection:
    databases: list[_DatabaseSection]
