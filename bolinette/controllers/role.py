from bolinette.routing import Namespace
from bolinette.services import role_service

ns = Namespace('/role', role_service)

ns.defaults.get_all(roles=['admin'])
ns.defaults.get_first_by('name', 'complete', roles=['admin'])
