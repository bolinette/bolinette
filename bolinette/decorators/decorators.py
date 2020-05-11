from typing import Type, Callable

from bolinette import core, db


def model(model_name: str):
    def decorator(model_cls: Type['db.defs.Model']):
        core.cache.models[model_name] = model_cls
        return model_cls
    return decorator


def init_func(func: Callable[[core.BolinetteContext], None]):
    core.cache.init_funcs.append(func)
    return func


def seeder(func):
    core.cache.seeders.append(func)
    return func
