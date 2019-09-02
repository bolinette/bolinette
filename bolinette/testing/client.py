import json

from bolinette import db


class TestClient:
    def __init__(self, bolinette):
        self.bolinette = bolinette
        self.bolinette.app.app_context().push()
        self.client = self.bolinette.app.test_client()
        self.cookies = {}

    def payload(self, **payload):
        if 'csrf_access_token' in self.cookies:
            payload['headers'] = {}
            payload['headers']['X-CSRF-TOKEN'] = self.cookies['csrf_access_token']
        return payload

    def parse_cookies(self, headers):
        for key, header in headers:
            if key == 'Set-Cookie':
                split = header.split(';')[0].split('=')
                self.cookies[split[0]] = split[1]

    def set_up(self):
        db.drop_all()
        db.create_all()

    def tear_down(self):
        self.client.cookie_jar.clear()
        db.drop_all()

    def post(self, path, data=None):
        if data is None:
            data = {}
        payload = self.payload(data=json.dumps(data),
                               content_type='application/json')
        res = self.client.post(f'/api{path}', **payload)
        self.parse_cookies(res.headers)
        return json.loads(res.data)

    def put(self, path, data=None):
        if data is None:
            data = {}
        payload = self.payload(data=json.dumps(data),
                               content_type='application/json')
        res = self.client.put(f'/api{path}', **payload)
        self.parse_cookies(res.headers)
        return json.loads(res.data)

    def patch(self, path, data=None):
        if data is None:
            data = {}
        payload = self.payload(data=json.dumps(data),
                               content_type='application/json')
        res = self.client.patch(f'/api{path}', **payload)
        self.parse_cookies(res.headers)
        return json.loads(res.data)

    def get(self, path):
        return json.loads(self.client.get(f'/api{path}', **self.payload()).data)

    def delete(self, path):
        return json.loads(self.client.delete(f'/api{path}', **self.payload()).data)
