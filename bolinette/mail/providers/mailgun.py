import requests
from bolinette.utils import logger

from bolinette import core


class Mailgun:
    def __init__(self, context: 'core.BolinetteContext'):
        self.url = context.env['MAILGUN_URL']
        self.ready = True
        self.key = context.env['MAILGUN_API']
        self.from_adr = context.env['MAILGUN_FROM']
        self._validate_attrs()

    def _validate_attrs(self):
        if not self.url:
            self.ready = False
            logger.error('MAILGUN_URL env key not set')
        if not self.key:
            self.ready = False
            logger.error('MAILGUN_API env key not set')
        if not self.from_adr:
            self.ready = False
            logger.error('MAILGUN_FROM env key not set')

    def send(self, to, subject, content):
        if self.ready:
            return requests.post(self.url, auth=("api", self.key), data={
                'from': self.from_adr,
                'to': list(to),
                'subject': subject,
                'text': content
            })
