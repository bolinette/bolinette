from typing import Dict

from bolinette import core, types


class Mixin:
    @staticmethod
    def columns() -> Dict[str, 'core.models.Column']:
        pass

    @staticmethod
    def relationships(model_cls) -> Dict[str, 'types.defs.Relationship']:
        pass
