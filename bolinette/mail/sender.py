from bolinette import env
from bolinette.mail.providers import Mailgun
from bolinette.utils import logger

_providers = {
    'mailgun': Mailgun
}


class Sender:
    def __init__(self):
        self.provider = None

    def init_app(self):
        provider = env['MAIL_PROVIDER']
        if provider:
            provider = provider.lower()
            if provider not in _providers:
                logger.warning(f'Unknown "{provider}" mail provider. '
                               f'Available: {", ".join(_providers.keys())}')
            else:
                self.provider = _providers[provider]()

    async def send(self, to, subject, content):
        if self.provider:
            try:
                self.provider.send(to, subject, content)
            except Exception as ex:
                logger.error(str(ex))


sender = Sender()
