from bolinette.data import service, Service

from example.entities import Library


@service('library')
class LibraryService(Service[Library]):
    ...
