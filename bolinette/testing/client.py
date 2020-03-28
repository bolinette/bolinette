import json

from bolinette.routing import serialize


class TestClient:
    def __init__(self, client):
        self.client = client
        self.cookies = {}

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
        return json.loads(await res.text())

    async def put(self, path: str, data: dict = None) -> dict:
        if data is None:
            data = {}
        res = await self.client.put(f'/api{path}', data=serialize(data, 'application/json')[0],
                                    headers={'Content-Type': 'application/json'})
        self.parse_cookies(res.headers)
        return json.loads(await res.text())

    async def patch(self, path: str, data: dict = None) -> dict:
        if data is None:
            data = {}
        res = await self.client.patch(f'/api{path}', data=serialize(data, 'application/json')[0],
                                      headers={'Content-Type': 'application/json'})
        self.parse_cookies(res.headers)
        return json.loads(await res.text())

    async def get(self, path: str) -> dict:
        res = await self.client.get(f'/api{path}')
        return json.loads(await res.text())

    async def delete(self, path: str) -> dict:
        res = await self.client.delete(f'/api{path}')
        return json.loads(await res.text())
