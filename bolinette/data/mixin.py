from typing import Dict

from bolinette import db


class Mixin:
    @staticmethod
    def columns() -> Dict[str, 'db.defs.Column']:
        pass

    @staticmethod
    def relationships(model_cls) -> Dict[str, 'db.defs.Relationship']:
        pass
