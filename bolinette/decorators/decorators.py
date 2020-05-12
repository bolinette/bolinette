from typing import Type, Callable

from bolinette import core, db, data


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


def service(service_name: str):
    def decorator(service_cls: Type['data.Service']):
        core.cache.services[service_name] = service_cls
        return service_cls
    return decorator
