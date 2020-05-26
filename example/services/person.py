from bolinette import blnt, core
from bolinette.decorators import service


@service('person')
class PersonService(blnt.Service):
    def __init__(self, context: 'core.BolinetteContext'):
        super().__init__(context)
