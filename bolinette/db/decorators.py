from typing import Type

from bolinette import db


def model(model_name: str):
    def decorator(model_cls: Type['db.defs.Model']):
        db.models.register(model_name, model_cls)
        return model_cls

    return decorator


def mixin(mixin_name: str):
    def decorator(mixin_class: Type['db.defs.Mixin']):
        db.mixins.register(mixin_name, mixin_class)
        return mixin_class

    return decorator


def with_mixin(mixin_name: str):
    def decorator(model_cls):
        mixin_cls = db.mixins.get(mixin_name)
        for col_name, col_def in mixin_cls.columns().items():
            setattr(model_cls, col_name, col_def)
        for rel_name, rel_def in mixin_cls.relationships(model_cls).items():
            setattr(model_cls, rel_name, rel_def)
        return model_cls

    return decorator


def model_property(function):
    return db.defs.ModelProperty(function.__name__, function)
