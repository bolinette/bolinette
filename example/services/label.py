from bolinette import core, blnt
from bolinette.decorators import service


@service('label')
class LabelService(core.Service):
    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)
