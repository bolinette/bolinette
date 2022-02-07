from bolinette.web.ctx import WebContext, WithWebContext
from bolinette.web.response import APIResponse, Response, Cookie
from bolinette.web.middleware import Middleware, MiddlewareMetadata, InternalMiddleware
from bolinette.web.controller import (
    Controller,
    ControllerMetadata,
    ControllerRoute,
    Expects,
    Returns,
    HttpMethod,
)
from bolinette.web.topic import Topic, TopicMetadata, TopicChannel
from bolinette.web.resources import BolinetteResources, BolinetteResource
from bolinette.web.sockets import BolinetteSockets
from bolinette.web.ext import ext
import bolinette.web.defaults as defaults
from bolinette.web.docs import Documentation
import bolinette.web.init as init

controller = ext.controller
route = ext.route
middleware = ext.middleware
