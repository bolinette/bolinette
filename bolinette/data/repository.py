from bolinette import core


class Repository:
    def __init__(self, name: str, model, db: 'core.DatabaseEngine'):
        self.name = name
        self.model = model
        self.db = db
