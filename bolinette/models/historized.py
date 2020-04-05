from bolinette import mapping, db
from bolinette.models import User
from sqlalchemy.ext.declarative.base import declared_attr


class Historized:
    created_on = db.defs.column(db.types.date)
    updated_on = db.defs.column(db.types.date)

    @declared_attr
    def created_by_id(self):
        return db.defs.column(db.types.integer, db.types.foreign_key('user', 'id'))

    @declared_attr
    def created_by(self):
        return db.defs.relationship(User, foreign_keys=self.created_by_id, lazy=False)

    @declared_attr
    def updated_by_id(self):
        return db.defs.column(db.types.integer, db.types.foreign_key('user', 'id'))

    @declared_attr
    def updated_by(self):
        return db.defs.relationship(User, foreign_keys=self.updated_by_id, lazy=False)

    @staticmethod
    def base_response():
        return [
            mapping.Field(db.types.date, key='created_on'),
            mapping.Field(db.types.date, key='updated_on'),
            mapping.Definition('created_by', 'user'),
            mapping.Definition('updated_by', 'user'),
        ]
