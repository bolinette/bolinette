from datetime import datetime

from bolinette import types, core, mapping
from bolinette.decorators import mixin


@mixin('historized')
class Historized(core.Mixin):
    def columns(self):
        return {
            'created_on': types.defs.Column(types.db.Date, nullable=False),
            'updated_on': types.defs.Column(types.db.Date, nullable=False),
            'created_by_id': types.defs.Column(
                types.db.Integer, reference=types.defs.Reference('user', 'id'), nullable=False),
            'updated_by_id': types.defs.Column(
                types.db.Integer, reference=types.defs.Reference('user', 'id'), nullable=False)
        }

    def relationships(self):
        return {
            'created_by': types.defs.Relationship('user', foreign_key="created_by_id", lazy=False),
            'updated_by': types.defs.Relationship('user', foreign_key="updated_by_id", lazy=False)
        }

    def response(self, model):
        return [
            mapping.Column(model.created_on),
            mapping.Column(model.updated_on),
            mapping.Reference(model.created_by),
            mapping.Reference(model.updated_by),
        ]

    @mixin.service_method
    async def create(self, values, current_user):
        if not current_user:
            return
        now = datetime.utcnow()
        values['created_on'] = now
        values['created_by_id'] = current_user.id
        values['updated_on'] = now
        values['updated_by_id'] = current_user.id

    @mixin.service_method
    async def update(self, entity, values, current_user):
        if not current_user:
            return
        now = datetime.utcnow()
        values['created_on'] = entity.created_on
        values['created_by_id'] = entity.created_by_id
        values['updated_on'] = now
        values['updated_by_id'] = current_user.id

    @mixin.service_method
    async def patch(self, values, current_user):
        if not current_user:
            return
        now = datetime.utcnow()
        values['updated_on'] = now
        values['updated_by_id'] = current_user.id
