from datetime import datetime, timedelta

import jwt as py_jwt

from bolinette import env
from bolinette.exceptions import UnauthorizedError


class JWT:
    def __init__(self):
        self.secret_key = None
        self._access_token_expires = timedelta(days=1)
        self._refresh_token_expires = timedelta(days=30)

    def access_token_expires(self, date):
        return date + self._access_token_expires

    def refresh_token_expires(self, date):
        return date + self._refresh_token_expires

    def init_app(self):
        self.secret_key = env['SECRET_KEY']

    def encode(self, payload):
        return py_jwt.encode(payload, self.secret_key, algorithm='HS256').decode('utf-8')

    def decode(self, token):
        return py_jwt.decode(token, self.secret_key, algorithm='HS256')

    def create_access_token(self, date, identity, *, fresh=False):
        payload = {
            'identity': identity,
            'fresh': fresh,
            'expires': str(self.access_token_expires(date))
        }
        return self.encode(payload)

    def create_refresh_token(self, date, identity):
        payload = {
            'identity': identity,
            'expires': str(self.refresh_token_expires(date))
        }
        return self.encode(payload)

    def verify(self, request, *, optional=False, fresh=False):
        now = datetime.utcnow()
        if 'access_token' in request.cookies:
            payload = self.decode(request.cookies['access_token'])
            expires = datetime.strptime(payload['expires'], '%Y-%m-%d %H:%M:%S.%f')
            if now > expires:
                raise UnauthorizedError('user.token.expired')
            if fresh and not payload['fresh']:
                raise UnauthorizedError('user.token.fresh_required')
            return payload['identity']
        if not optional:
            raise UnauthorizedError('user.unauthorized')
        return None


jwt = JWT()
