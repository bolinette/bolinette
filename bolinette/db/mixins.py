from typing import Type, Dict

from bolinette import db


def mixin(mixin_name: str):
    def decorator(mixin_class: Type['db.defs.Mixin']):
        mixins.register(mixin_name, mixin_class)
        return mixin_class

    return decorator


class Mixins:
    def __init__(self):
        self.registered: Dict[str, Type['db.defs.Mixin']] = {}

    def get(self, mixin_name: str) -> Type['db.defs.Mixin']:
        return self.registered[mixin_name]

    def register(self, mixin_name: str, mixin_class: Type['db.defs.Mixin']):
        self.registered[mixin_name] = mixin_class


mixins = Mixins()


def with_mixin(mixin_name: str):
    def decorator(model_cls):
        mixin_cls = mixins.get(mixin_name)
        for col_name, col_def in mixin_cls.columns().items():
            setattr(model_cls, col_name, col_def)
        for rel_name, rel_def in mixin_cls.relationships(model_cls).items():
            setattr(model_cls, rel_name, rel_def)
        return model_cls

    return decorator
