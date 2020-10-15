from bolinette.utils import logger

from bolinette import core
from bolinette.mail.providers import Mailgun

_providers = {
    'mailgun': Mailgun
}


class Sender:
    def __init__(self, context: 'core.BolinetteContext'):
        self.context = context
        self.provider = None

    def init_app(self):
        provider = self.context.env['MAIL_PROVIDER']
        if provider:
            provider = provider.lower()
            if provider not in _providers:
                logger.warning(f'Unknown "{provider}" mail provider. '
                               f'Available: {", ".join(_providers.keys())}')
            else:
                self.provider = _providers[provider](self.context)

    async def send(self, to, subject, content):
        if self.provider:
            try:
                self.provider.send(to, subject, content)
            except Exception as ex:
                logger.error(str(ex))
