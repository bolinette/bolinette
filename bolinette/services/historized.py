from datetime import datetime

from bolinette.services import BaseService


class HistorizedService(BaseService):
    def __init__(self, model):
        super().__init__(model)

    async def create(self, values, *, current_user=None, **_):
        if current_user:
            now = datetime.utcnow()
            values['created_on'] = now
            values['created_by_id'] = current_user.id
            values['updated_on'] = now
            values['updated_by_id'] = current_user.id
        return await super().create(values, **_)

    async def update(self, entity, values, *, current_user=None, **_):
        if current_user:
            now = datetime.utcnow()
            values['created_on'] = entity.created_on
            values['created_by_id'] = entity.created_by_id
            values['updated_on'] = now
            values['updated_by_id'] = current_user.id
        return await super().update(entity, values, **_)

    async def patch(self, entity, values, *, current_user=None, **_):
        if current_user:
            now = datetime.utcnow()
            values['updated_on'] = now
            values['updated_by_id'] = current_user.id
        return await super().patch(entity, values, **_)
