from bolinette import Namespace
from bolinette.services import role_service

ns = Namespace(role_service, '/role')

ns.defaults.get_all(roles=['admin'])
ns.defaults.get_first_by('name', 'complete', roles=['admin'])

ns.register()
