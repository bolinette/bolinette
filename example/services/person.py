from bolinette.services import BaseService


class PersonService(BaseService):
    def __init__(self):
        super().__init__('person')


person_service = PersonService()
