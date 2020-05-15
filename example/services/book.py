from bolinette import data, core
from bolinette.decorators import service


@service('book')
class BookService(data.HistorizedService):
    def __init__(self, context: 'core.BolinetteContext'):
        super().__init__(context)
