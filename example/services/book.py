from bolinette import core, blnt
from bolinette.decorators import service


@service('book')
class BookService(core.HistorizedService):
    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)
