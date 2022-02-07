import pytz

from bolinette.data import ext, SimpleService


@ext.service("tz")
class TimezoneService(SimpleService):
    @staticmethod
    async def get_all():
        return [tz for tz in pytz.all_timezones]

    @staticmethod
    async def is_valid(key):
        return key in pytz.all_timezones
