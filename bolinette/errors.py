from flask import Response

from bolinette import response, env
from bolinette.namespaces import serialize


def _error_handler(error, message, func):
    res, code = func(error.description if env['DEBUG'] else message)
    res, mime = serialize(res)
    return Response(res, code, mimetype=mime)


def init_error_handlers(app):
    app.errorhandler(404)(
        lambda error: _error_handler(error, 'global.resource_not_found', response.not_found)
    )
    app.errorhandler(500)(
        lambda error: _error_handler(error, 'global.internal_error', response.internal_server_error)
    )
