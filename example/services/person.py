from bolinette import data, core
from bolinette.decorators import service


@service('person')
class PersonService(data.Service):
    def __init__(self, name, context: 'core.BolinetteContext'):
        super().__init__(name, context)
