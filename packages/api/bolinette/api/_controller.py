from muotti import Mapper
from soupape import post_init
from sqlalchemy.orm import DeclarativeBase

from bolinette.data.relational import Service
from bolinette.web import Controller


class ApiController[EntityT: DeclarativeBase](Controller):
    _service: Service[EntityT]
    _mapper: Mapper

    @post_init
    def _init_api_controller(self, service: Service[EntityT], mapper: Mapper) -> None:
        self._service = service
        self._mapper = mapper

    @property
    def service(self) -> Service[EntityT]:
        return self._service

    @property
    def mapper(self) -> Mapper:
        return self._mapper

    @property
    def entity(self) -> type[EntityT]:
        return self._service.entity
