from bolinette.core import BolinetteContext
from bolinette.data import DataContext, service, Service


@service('person')
class PersonService(Service):
    def __init__(self, context: BolinetteContext, data_ctx: DataContext):
        super().__init__(context, data_ctx)
