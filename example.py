from bolinette import data, web
from bolinette.core import Bolinette


def make_bolinette() -> Bolinette:
    blnt = Bolinette()
    blnt.use_extension(data)
    blnt.use_extension(web).use_sockets().use_blnt_auth()
    return blnt.build()
