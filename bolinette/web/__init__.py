from bolinette.web.route import (
    route as route,
    get as get,
    post as post,
    put as put,
    patch as patch,
    delete as delete,
)
from bolinette.web.controller import Controller as Controller, controller as controller
from bolinette.web.middleware import (
    with_middleware as with_middleware,
    without_middleware as without_middleware,
)
from bolinette.web.payload import Payload as Payload
from bolinette.web.resources import WebResources as WebResources
from bolinette.web.extension import web_ext as __blnt_ext__
