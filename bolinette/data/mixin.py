from typing import Dict

from bolinette import types


class Mixin:
    @staticmethod
    def columns() -> Dict[str, 'types.Column']:
        pass

    @staticmethod
    def relationships(model_cls) -> Dict[str, 'types.Relationship']:
        pass
