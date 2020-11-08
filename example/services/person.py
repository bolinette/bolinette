from bolinette import core, blnt
from bolinette.decorators import service


@service('person')
class PersonService(core.Service):
    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)
