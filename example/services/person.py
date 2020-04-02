from bolinette.services import BaseService
from example.models import Person


class PersonService(BaseService):
    def __init__(self):
        super().__init__(Person)


person_service = PersonService()
