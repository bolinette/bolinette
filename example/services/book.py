from bolinette import data, core
from bolinette.decorators import service


@service('book')
class BookService(data.HistorizedService):
    def __init__(self, name, context: 'core.BolinetteContext'):
        super().__init__(name, context)
