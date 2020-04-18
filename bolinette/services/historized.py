from datetime import datetime

from bolinette.services import BaseService


class HistorizedService(BaseService):
    def __init__(self, model):
        super().__init__(model)

    async def create(self, params, *, current_user=None, **_):
        if current_user:
            now = datetime.utcnow()
            params['created_on'] = now
            params['created_by_id'] = current_user.id
            params['updated_on'] = now
            params['updated_by_id'] = current_user.id
        return await super().create(params, **_)

    async def update(self, entity, params, *, current_user=None, **_):
        if current_user:
            now = datetime.utcnow()
            params['created_on'] = entity.created_on
            params['created_by_id'] = entity.created_by_id
            params['updated_on'] = now
            params['updated_by_id'] = current_user.id
        return await super().update(entity, params, **_)

    async def patch(self, entity, params, *, current_user=None, **_):
        if current_user:
            now = datetime.utcnow()
            params['updated_on'] = now
            params['updated_by_id'] = current_user.id
        return await super().patch(entity, params, **_)
