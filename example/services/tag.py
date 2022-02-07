from bolinette.data import service, Service

from example.entities import Tag


@service("tag")
class TagService(Service[Tag]):
    ...
