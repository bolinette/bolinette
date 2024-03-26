from bolinette.web.asgi import AsgiApplication
from example import make_bolinette

blnt = make_bolinette()
app = AsgiApplication(blnt).get_app()
