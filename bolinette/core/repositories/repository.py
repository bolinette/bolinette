from bolinette import blnt, core


class Repository:
    def __init__(self, name: str, model: 'core.Model', context: 'blnt.BolinetteContext'):
        self.name = name
        self.model = model
        self.context = context

    async def get_all(self, pagination=None, order_by=None):
        raise NotImplementedError()

    async def get(self, identifier):
        raise NotImplementedError()

    async def get_by(self, key, value):
        raise NotImplementedError()

    async def get_first_by(self, key, value):
        raise NotImplementedError()

    async def get_by_criteria(self, criteria):
        raise NotImplementedError()

    async def create(self, values):
        raise NotImplementedError()

    async def update(self, entity, values):
        raise NotImplementedError()

    async def patch(self, entity, values):
        raise NotImplementedError()

    async def delete(self, entity):
        raise NotImplementedError()
