from bolinette import mapping, db


class Historized(db.types.Model):
    created_on = db.types.Column(db.types.Date)
    updated_on = db.types.Column(db.types.Date)
    created_by_id = db.types.Column(db.types.Integer, reference=db.types.Reference('user', 'id'))
    created_by = db.types.Relationship('user', foreign_key=created_by_id, lazy=False)
    updated_by_id = db.types.Column(db.types.Integer, reference=db.types.Reference('user', 'id'))
    updated_by = db.types.Relationship('user', foreign_key=updated_by_id, lazy=False)

    @classmethod
    def base_response(cls):
        return [
            mapping.Column(cls.created_on),
            mapping.Column(cls.updated_on),
            mapping.Reference(cls.created_by),
            mapping.Reference(cls.updated_by),
        ]
