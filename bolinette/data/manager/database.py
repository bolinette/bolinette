from sqlalchemy import table

from bolinette.core import injectable
from bolinette.data import DataSection, __data_cache__
from bolinette.data.manager import EntityManager


@injectable(cache=__data_cache__)
class DatabaseManager:
    def __init__(self, section: DataSection, entities: EntityManager) -> None:
        self._section = section
        self._entities = entities
