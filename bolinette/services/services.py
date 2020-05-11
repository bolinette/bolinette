from typing import Dict, Union

from bolinette import services, db, mapping, core

_registered_services: Dict[str, 'services.BaseService'] = {}


def register(service: Union['services.BaseService', 'services.SimpleService']):
    _registered_services[service.name] = service


def get(name: str):
    return _registered_services[name]


def init_services():
    for name, service in _registered_services.items():
        if isinstance(service, services.BaseService):
            service.model = core.cache.models.get(name)
            if issubclass(service.model, db.defs.Model):
                mapping.register(name, service.model)
