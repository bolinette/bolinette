import json
from asyncio.events import AbstractEventLoop

from aiohttp import test_utils

import bolinette
from bolinette import abc
from bolinette.testing import Mock
from bolinette.utils.serializing import serialize


class BolitestClient(abc.WithContext):
    def __init__(self, blnt_app: 'bolinette.Bolinette', loop: AbstractEventLoop):
        super().__init__(blnt_app.context)
        server = test_utils.TestServer(blnt_app.app, loop=loop)
        self.client = test_utils.TestClient(server, loop=loop)
        self.mock = Mock(blnt_app.context)
        self.cookies = {}

    async def __aenter__(self):
        await self.client.start_server()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.close()

    def __await__(self):
        return self.__aenter__().__await__()

    def try_parse(self, response):
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return response

    def payload(self, **payload):
        if 'csrf_access_token' in self.cookies:
            payload['headers'] = {}
            payload['headers']['X-CSRF-TOKEN'] = self.cookies['csrf_access_token']
        return payload

    def parse_cookies(self, headers):
        for key, header in headers.items():
            if key == 'Set-Cookie':
                split = header.split(';')[0].split('=')
                self.cookies[split[0]] = split[1]

    async def post(self, path: str, data: dict = None, *, prefix='/api') -> dict:
        if data is None:
            data = {}
        res = await self.client.post(f'{prefix}{path}', data=serialize(data, 'application/json')[0],
                                     headers={'Content-Type': 'application/json'})
        self.parse_cookies(res.headers)
        text = await res.text()
        return self.try_parse(text)

    async def put(self, path: str, data: dict = None, *, prefix='/api') -> dict:
        if data is None:
            data = {}
        res = await self.client.put(f'{prefix}{path}', data=serialize(data, 'application/json')[0],
                                    headers={'Content-Type': 'application/json'})
        self.parse_cookies(res.headers)
        text = await res.text()
        return self.try_parse(text)

    async def patch(self, path: str, data: dict = None, *, prefix='/api') -> dict:
        if data is None:
            data = {}
        res = await self.client.patch(f'{prefix}{path}', data=serialize(data, 'application/json')[0],
                                      headers={'Content-Type': 'application/json'})
        self.parse_cookies(res.headers)
        text = await res.text()
        return self.try_parse(text)

    async def get(self, path: str, *, prefix='/api') -> dict:
        res = await self.client.get(f'{prefix}{path}')
        text = await res.text()
        return self.try_parse(text)

    async def delete(self, path: str, *, prefix='/api') -> dict:
        res = await self.client.delete(f'{prefix}{path}')
        text = await res.text()
        return self.try_parse(text)
