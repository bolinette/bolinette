from aiohttp import web as aio_web

from bolinette import env
from bolinette.routing import web
from bolinette.commands import command


@command('run_server')
def run_server():
    aio_web.run_app(web.app, port=env['PORT'])
