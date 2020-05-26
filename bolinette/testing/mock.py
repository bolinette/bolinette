import datetime
import random
import string
from types import SimpleNamespace

from bolinette import core, types


class Mocked:
    def __init__(self, name, context: core.BolinetteContext):
        self.name = name
        self.context = context
        self.fields = SimpleNamespace()

    @staticmethod
    def insert_entity(context: core.BolinetteContext, name, params):
        entity = context.table(name)(**params)
        context.db.session.add(entity)
        return entity

    def insert(self):
        fields = {}
        for key, value in self.fields.__dict__.items():
            fields[key] = value
        return self.insert_entity(self.context, self.name, fields)

    def to_response(self, key='default') -> dict:
        definition = self.context.mapping.response(self.name, key)
        return self.context.mapping.marshall(definition, self.fields, use_foreign_key=True)

    def to_payload(self, key='default') -> dict:
        definition = self.context.mapping.payload(self.name, key)
        return self.context.mapping.marshall(definition, self.fields, use_foreign_key=True)


class Mock:
    def __init__(self, context: core.BolinetteContext):
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
        columns = self.context.model(model_name).__props__.get_columns()
        rng = random.Random(hash(f'{model_name}.{m_id}'))
        mocked = Mocked(model_name, self.context)
        for _, column in columns.items():
            if column.primary_key:
                continue
            col_type = column.type
            if col_type == types.db.String:
                setattr(mocked.fields, column.name, self._random_lower(rng, 15))
            if col_type == types.db.Email:
                setattr(mocked.fields, column.name, f'{self._random_lower(rng, 10)}@{self._random_lower(rng, 5)}.com')
            if col_type == types.db.Password:
                setattr(mocked.fields, column.name, (self._random_lower(rng, 10) + str(self._random_int(rng, 1, 100))
                                                     + self._random_symbols(rng, 1)))
            if col_type == types.db.Integer:
                setattr(mocked.fields, column.name, self._random_int(rng, 1, 100))
            if col_type == types.db.Float:
                setattr(mocked.fields, column.name, self._random_int(rng, 1, 100))
            if col_type == types.db.Date:
                setattr(mocked.fields, column.name, self._random_date(rng, datetime.datetime(1900, 1, 1),
                                                                      datetime.datetime(2000, 1, 1)))
        if post_mock_fn and callable(post_mock_fn):
            post_mock_fn(mocked)
        return mocked
