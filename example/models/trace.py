from bolinette import types
from bolinette.data import Model, model


@model("trace")
class TraceModel(Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    name = types.defs.Column(types.db.String, nullable=False)
    visits = types.defs.Column(types.db.Integer, nullable=False)
    last_visit = types.defs.Column(types.db.Date, nullable=False)
    user_id = types.defs.Column(
        types.db.Integer, nullable=False, reference=types.defs.Reference("user", "id")
    )
    user = types.defs.Relationship(
        "user",
        foreign_key="user_id",
        lazy=False,
        backref=types.defs.Backref("traces", lazy=True),
    )
