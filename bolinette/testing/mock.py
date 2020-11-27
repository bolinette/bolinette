import datetime
import random
import string
from types import SimpleNamespace
from typing import Dict, Any

from bolinette import blnt, types


class Mocked:
    def __init__(self, name, context: 'blnt.BolinetteContext'):
        self.context = context
        self.name = name
        self.model = self.context.model(self.name)
        self.database = self.context.db[self.model.__blnt__.database]
        self._fields = {}

    def __getitem__(self, key):
        return self._fields[key]

    def __setitem__(self, key, value):
        self._fields[key] = value

    def __contains__(self, key):
        return key in self._fields

    @staticmethod
    async def insert_entity(context: 'blnt.BolinetteContext', name: str, params: Dict[str, Any]):
        mocked = Mocked(name, context)
        for key, value in params.items():
            mocked[key] = value
        return await mocked.insert()

    @property
    def _to_object(self):
        obj = SimpleNamespace()
        for key, value in self._fields.items():
            setattr(obj, key, value)
        return obj

    async def insert(self):
        return await self.context.repo(self.name).create(self._fields)

    def to_response(self, key='default') -> dict:
        definition = self.context.mapper.response(self.name, key)
        return self.context.mapper.marshall(
            definition,
            self._to_object if self.database.relational else self._fields,
            use_foreign_key=True
        )

    def to_payload(self, key='default') -> dict:
        definition = self.context.mapper.payload(self.name, key)
        return self.context.mapper.marshall(
            definition,
            self._to_object if self.database.relational else self._fields,
            use_foreign_key=True
        )


class Mock:
    def __init__(self, context: 'blnt.BolinetteContext'):
        self._id = None
        self.context = context

    def _random_lower(self, rng, length):
        return ''.join(rng.choices(string.ascii_lowercase, k=length))

    def _random_symbols(self, rng, length):
        return ''.join(rng.choices(string.punctuation, k=length))

    def _random_int(self, rng, a, b):
        return rng.randint(a, b)

    def _random_decimal(self, rng, a, b):
        return rng.uniform(a, b)

    def _random_date(self, rng, start_date, end_date):
        time_between_dates = end_date - start_date
        days_between_dates = time_between_dates.days
        random_number_of_days = rng.randrange(days_between_dates)
        return start_date + datetime.timedelta(days=random_number_of_days)

    def __call__(self, m_id, model_name, *, post_mock_fn=None):
        self._id = m_id
        columns = self.context.model(model_name).__props__.get_columns()
        rng = random.Random(hash(f'{model_name}.{m_id}'))
        mocked = Mocked(model_name, self.context)
        for _, column in columns.items():
            if column.primary_key:
                continue
            col_type = column.type
            if col_type == types.db.String:
                mocked[column.name] = self._random_lower(rng, 15)
            if col_type == types.db.Email:
                mocked[column.name] = f'{self._random_lower(rng, 10)}@{self._random_lower(rng, 5)}.com'
            if col_type == types.db.Password:
                mocked[column.name] = (self._random_lower(rng, 10) + str(self._random_int(rng, 1, 100))
                                       + self._random_symbols(rng, 1))
            if col_type == types.db.Integer:
                mocked[column.name] = self._random_int(rng, 1, 100)
            if col_type == types.db.Float:
                mocked[column.name] = self._random_int(rng, 1, 100)
            if col_type == types.db.Date:
                mocked[column.name] = self._random_date(rng, datetime.datetime(1900, 1, 1),
                                                        datetime.datetime(2000, 1, 1))
        if post_mock_fn and callable(post_mock_fn):
            post_mock_fn(mocked)
        return mocked
