from bolinette.network import AccessToken
from bolinette.web import Namespace
from example.services import book_service

ns = Namespace('/book', book_service)

ns.defaults.get_all()
ns.defaults.get_one('complete')
ns.defaults.create('complete', access=AccessToken.Required)
ns.defaults.update('complete', access=AccessToken.Required)
ns.defaults.patch('complete', access=AccessToken.Required)
ns.defaults.delete('complete', access=AccessToken.Required)
