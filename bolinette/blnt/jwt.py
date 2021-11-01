from datetime import datetime, timedelta

import jwt as py_jwt

from bolinette import abc, blnt
from bolinette.exceptions import UnauthorizedError


class JWT(abc.WithContext):
    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)
        self._access_token_expires = timedelta(seconds=context.env['access_token_validity'])
        self._refresh_token_expires = timedelta(seconds=context.env['refresh_token_validity'])

    def access_token_expires(self, date):
        return date + self._access_token_expires

    def refresh_token_expires(self, date):
        return date + self._refresh_token_expires

    @property
    def secret_key(self):
        return self.context.env['secret_key']

    def encode(self, payload):
        return py_jwt.encode(payload, self.secret_key, algorithm='HS256')

    def decode(self, token):
        return py_jwt.decode(token, self.secret_key, algorithms='HS256')

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

    def verify(self, token: str | None, *, optional=False, fresh=False):
        now = datetime.utcnow()
        if token:
            try:
                payload = self.decode(token)
            except py_jwt.PyJWTError:
                if optional:
                    return None
                raise UnauthorizedError('user.token.invalid')
            expires = datetime.strptime(payload['expires'], '%Y-%m-%d %H:%M:%S.%f')
            if now > expires:
                raise UnauthorizedError('user.token.expired')
            if fresh and not payload['fresh']:
                raise UnauthorizedError('user.token.fresh_required')
            return payload['identity']
        if not optional:
            raise UnauthorizedError('user.unauthorized')
        return None
