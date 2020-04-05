from bolinette.services import BaseService


class HistorizedService(BaseService):
    def __init__(self, model):
        super().__init__(model)
