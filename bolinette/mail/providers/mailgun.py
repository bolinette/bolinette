import requests

from bolinette import abc, blnt


class Mailgun(abc.WithContext):
    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)
        self.url = context.env['mailgun_url']
        self.ready = True
        self.key = context.env['mailgun_api']
        self.from_adr = context.env['mailgun_from']
        self._validate_attrs()

    def _validate_attrs(self):
        if not self.url:
            self.ready = False
            self.context.logger.error('MAILGUN_URL env key not set')
        if not self.key:
            self.ready = False
            self.context.logger.error('MAILGUN_API env key not set')
        if not self.from_adr:
            self.ready = False
            self.context.logger.error('MAILGUN_FROM env key not set')

    def send(self, to, subject, content):
        if self.ready:
            return requests.post(self.url, auth=("api", self.key), data={
                'from': self.from_adr,
                'to': list(to),
                'subject': subject,
                'text': content
            })
