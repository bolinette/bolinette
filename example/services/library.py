from bolinette import core, blnt
from bolinette.decorators import service


@service('library')
class LibraryService(core.Service):
    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)
