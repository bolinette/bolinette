from bolinette.routing import Namespace
from example.services import book_service

ns = Namespace(book_service, '/book')

ns.defaults.get_all()
ns.defaults.get_one('complete')
ns.defaults.create('complete')
ns.defaults.update('complete')
ns.defaults.patch('complete')
ns.defaults.delete('complete')

ns.register()
