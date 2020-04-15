from typing import Type, Dict

from bolinette import db


class Mixins:
    def __init__(self):
        self.registered: Dict[str, Type['db.defs.Mixin']] = {}

    def get(self, mixin_name: str) -> Type['db.defs.Mixin']:
        return self.registered[mixin_name]

    def register(self, mixin_name: str, mixin_class: Type['db.defs.Mixin']):
        self.registered[mixin_name] = mixin_class


mixins = Mixins()
