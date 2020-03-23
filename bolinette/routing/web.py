from aiohttp import web as aio_web
import aiohttp_cors


class Web:
    def __init__(self):
        self.app = None
        self.cors = None

    def init_app(self):
        self.app = aio_web.Application()
        self.cors = aiohttp_cors.setup(self.app)


web = Web()
