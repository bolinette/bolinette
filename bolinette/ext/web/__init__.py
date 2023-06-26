from bolinette.ext.web.version import __version__
from bolinette.ext.web.route import (
    route as route,
    get as get,
    post as post,
    put as put,
    patch as patch,
    delete as delete,
)
from bolinette.ext.web.controller import Controller as Controller, controller as controller
from bolinette.ext.web.resources import WebResources
