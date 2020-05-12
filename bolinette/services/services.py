from typing import Dict, Union

from bolinette import services, mapping, core, data

_registered_services: Dict[str, 'services.BaseService'] = {}


def register(service: Union['services.BaseService', 'services.SimpleService']):
    _registered_services[service.name] = service


def get(name: str):
    return _registered_services[name]


def init_services(context: core.BolinetteContext):
    for name, service in _registered_services.items():
        if isinstance(service, services.BaseService):
            service.model = context.models.get(name)
            if isinstance(service.model, data.Model):
                mapping.register(name, service.model)
