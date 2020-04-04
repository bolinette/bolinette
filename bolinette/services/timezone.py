import pytz

from bolinette.services import SimpleService


class TimezoneService(SimpleService):
    def __init__(self):
        super().__init__('tz')

    async def get_all(self):
        return [tz for tz in pytz.all_timezones]

    async def is_valid(self, key):
        return key in pytz.all_timezones


timezone_service = TimezoneService()
