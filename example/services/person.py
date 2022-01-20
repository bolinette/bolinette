from bolinette.data import service, Service

from example.entities import Person


@service('person')
class PersonService(Service[Person]):
    ...
