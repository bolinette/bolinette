from bolinette import blnt, core
from bolinette.decorators import service


@service('book')
class BookService(blnt.HistorizedService):
    def __init__(self, context: 'core.BolinetteContext'):
        super().__init__(context)
