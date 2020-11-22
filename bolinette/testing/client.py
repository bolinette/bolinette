import json
from asyncio.events import AbstractEventLoop

from aiohttp import test_utils

import bolinette
from bolinette.testing import Mock
from bolinette.utils.serializing import serialize


class TestClient:
    def __init__(self, blnt_app: 'bolinette.Bolinette', loop: AbstractEventLoop):
        server = test_utils.TestServer(blnt_app.app, loop=loop)
        self.client = test_utils.TestClient(server, loop=loop)
        self.context = blnt_app.context
        self.mock = Mock(blnt_app.context)
        self.cookies = {}

    async def __aenter__(self):
        await self.client.start_server()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.close()

    def __await__(self):
        return self.__aenter__().__await__()

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

    async def post(self, path: str, data: dict = None) -> dict:
        if data is None:
            data = {}
        res = await self.client.post(f'/api{path}', data=serialize(data, 'application/json')[0],
                                     headers={'Content-Type': 'application/json'})
        self.parse_cookies(res.headers)
        text = await res.text()
        return json.loads(text)

    async def put(self, path: str, data: dict = None) -> dict:
        if data is None:
            data = {}
        res = await self.client.put(f'/api{path}', data=serialize(data, 'application/json')[0],
                                    headers={'Content-Type': 'application/json'})
        self.parse_cookies(res.headers)
        text = await res.text()
        return json.loads(text)

    async def patch(self, path: str, data: dict = None) -> dict:
        if data is None:
            data = {}
        res = await self.client.patch(f'/api{path}', data=serialize(data, 'application/json')[0],
                                      headers={'Content-Type': 'application/json'})
        self.parse_cookies(res.headers)
        text = await res.text()
        return json.loads(text)

    async def get(self, path: str) -> dict:
        res = await self.client.get(f'/api{path}')
        text = await res.text()
        return json.loads(text)

    async def delete(self, path: str) -> dict:
        res = await self.client.delete(f'/api{path}')
        text = await res.text()
        return json.loads(text)
