from bolinette import Namespace
from example.services import person_service

ns = Namespace(person_service, '/person')

ns.defaults.get_all()
ns.defaults.get_one('complete')
ns.defaults.create('complete')
ns.defaults.update('complete')
ns.defaults.patch('complete')
ns.defaults.delete('complete')

ns.register()
