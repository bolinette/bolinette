from bolinette import core, blnt
from bolinette.decorators import service


@service('tag')
class TagService(core.Service):
    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)
