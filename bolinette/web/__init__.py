from bolinette.web.version import __version__
from bolinette.web.route import (
    route as route,
    get as get,
    post as post,
    put as put,
    patch as patch,
    delete as delete,
)
from bolinette.web.controller import Controller as Controller, controller as controller
from bolinette.web.middleware import with_middleware as with_middleware, without_middleware as without_middleware
from bolinette.web.resources import WebResources as WebResources
