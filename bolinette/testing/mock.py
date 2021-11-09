import datetime
import random
import string
from types import SimpleNamespace
from typing import Any

from bolinette import abc, blnt, types, core


class Mocked(abc.WithContext):
    def __init__(self, name, context: 'blnt.BolinetteContext'):
        super().__init__(context)
        self.name = name
        self.model = self.context.inject.require('model', self.name, immediate=True)
        self.database = self.context.db[self.model.__blnt__.database]
        self._fields = {}

    def __getitem__(self, key):
        return self._fields[key]

    def __setitem__(self, key, value):
        self._fields[key] = value

    def __contains__(self, key):
        return key in self._fields

    def __repr__(self):
        return repr(self._fields)

    @staticmethod
    async def insert_entity(context: 'blnt.BolinetteContext', name: str, params: dict[str, Any]):
        mocked = Mocked(name, context)
        for key, value in params.items():
            mocked[key] = value
        return await mocked.insert()

    @property
    def _to_object(self):
        def __to_object(values: dict[str, Any]):
            obj = SimpleNamespace()
            for key, value in values.items():
                if isinstance(value, dict):
                    value = __to_object(value)
                setattr(obj, key, value)
            return obj
        return __to_object(self._fields)

    @property
    def fields(self):
        return dict(self._fields)

    async def insert(self):
        return (await self.context.inject.require('model', self.name, immediate=True)
                      .__props__.repo.create(self._fields))

    def to_response(self, key='default') -> dict:
        definition = self.context.mapper.response(self.name, key)
        return self.context.mapper.marshall(
            definition,
            self._to_object if self.database.relational else self._fields
        )

    def to_payload(self, key='default') -> dict:
        definition = self.context.mapper.payload(self.name, key)
        return self.context.mapper.marshall(
            definition,
            self._to_object if self.database.relational else self._fields
        )


class Mock(abc.WithContext):
    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)

    @staticmethod
    def _random_lower(rng, length):
        return ''.join(rng.choices(string.ascii_lowercase, k=length))

    @staticmethod
    def _random_symbols(rng, length):
        return ''.join(rng.choices(string.punctuation, k=length))

    @staticmethod
    def _random_int(rng, a, b):
        return rng.randint(a, b)

    @staticmethod
    def _random_decimal(rng, a, b):
        return rng.uniform(a, b)

    @staticmethod
    def _random_date(rng, start_date, end_date):
        time_between_dates = end_date - start_date
        days_between_dates = time_between_dates.days
        random_number_of_days = rng.randrange(days_between_dates)
        return start_date + datetime.timedelta(days=random_number_of_days)

    def __call__(self, m_id, model_name, *, post_mock_fn=None):
        def _get_random_value(_col_type):
            match _col_type:
                case types.db.String:
                    return Mock._random_lower(rng, 15)
                case types.db.Email:
                    return f'{Mock._random_lower(rng, 10)}@{Mock._random_lower(rng, 5)}.com'
                case types.db.Password:
                    return (Mock._random_lower(rng, 10) + str(Mock._random_int(rng, 1, 100))
                            + Mock._random_symbols(rng, 1))
                case types.db.Integer:
                    return Mock._random_int(rng, 1, 100)
                case types.db.Float:
                    return Mock._random_int(rng, 1, 100)
                case types.db.Date:
                    return Mock._random_date(rng, datetime.datetime(1900, 1, 1),
                                             datetime.datetime(2000, 1, 1))
                case _:
                    return None

        rng = random.Random(hash(f'{model_name}.{m_id}'))
        mocked = Mocked(model_name, self.context)
        model: core.Model = self.context.inject.require('model', model_name, immediate=True)
        columns = model.__props__.get_columns()
        for _, column in columns:
            if column.auto_increment:
                continue
            if column.reference is not None:
                mocked[column.name] = None
            else:
                mocked[column.name] = _get_random_value(column.type)

        back_refs = model.__props__.get_back_refs()
        for att_name, _ in back_refs:
            mocked[att_name] = []
        if post_mock_fn and callable(post_mock_fn):
            post_mock_fn(mocked)
        return mocked
