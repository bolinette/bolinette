from bolinette.web import Namespace, AccessType
from example.services import book_service

ns = Namespace('/book', book_service)

ns.defaults.get_all()
ns.defaults.get_one('complete')
ns.defaults.create('complete', access=AccessType.Required)
ns.defaults.update('complete', access=AccessType.Required)
ns.defaults.patch('complete', access=AccessType.Required)
ns.defaults.delete('complete', access=AccessType.Required)
