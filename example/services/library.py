from bolinette import data, core
from bolinette.decorators import service


@service('library')
class LibraryService(data.Service):
    def __init__(self, context: 'core.BolinetteContext'):
        super().__init__(context)
