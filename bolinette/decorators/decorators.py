from typing import Type, Callable

from bolinette import core, data


def model(model_name: str):
    def decorator(model_cls: Type['data.Model']):
        core.cache.models[model_name] = model_cls
        return model_cls
    return decorator


def mixin(mixin_name: str):
    def decorator(mixin_cls: Type['data.Mixin']):
        core.cache.mixins[mixin_name] = mixin_cls
        return mixin_cls
    return decorator


def with_mixin(mixin_name: str):
    def decorator(model_cls):
        mixin_cls = core.cache.mixins.get(mixin_name)
        for col_name, col_def in mixin_cls.columns().items():
            setattr(model_cls, col_name, col_def)
        for rel_name, rel_def in mixin_cls.relationships(model_cls).items():
            setattr(model_cls, rel_name, rel_def)
        return model_cls
    return decorator


def init_func(func: Callable[[core.BolinetteContext], None]):
    core.cache.init_funcs.append(func)
    return func


def seeder(func):
    core.cache.seeders.append(func)
    return func


def service(service_name: str):
    def decorator(service_cls: Type['data.Service']):
        core.cache.services[service_name] = service_cls
        return service_cls
    return decorator
