from bolinette.core.injection import post_init
from bolinette.core.mapping import Mapper
from bolinette.data.relational import DeclarativeBase, Service


class ApiController[EntityT: DeclarativeBase]:
    def __init__(self) -> None:
        self.service: Service[EntityT]
        self.mapper: Mapper
        self.cls: type[EntityT]

    @post_init
    def _init_base_class(self, service: Service[EntityT], mapper: Mapper, cls: type[EntityT]) -> None:
        self.service = service
        self.mapper = mapper
        self.cls = cls
