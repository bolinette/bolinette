import datetime
import random
import string
from types import SimpleNamespace

from bolinette import db, mapping


class Mocked:
    def __init__(self, name):
        self.name = name
        self.fields = SimpleNamespace()

    @staticmethod
    def insert_entity(entity) -> db.engine.model:
        db.engine.session.add(entity)
        return entity

    def insert(self, model) -> db.engine.model:
        fields = {}
        for key, value in self.fields.__dict__.items():
            fields[key] = value
        return self.insert_entity(model(**fields))

    def to_response(self, key='default') -> dict:
        definition = mapping.get_response(self.name, key)
        return mapping.marshall(definition, self.fields, use_foreign_key=True)

    def to_payload(self, key='default') -> dict:
        definition = mapping.get_payload(self.name, key)
        return mapping.marshall(definition, self.fields, use_foreign_key=True)


class Mock:
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
        model = db.models.get(model_name)
        columns = model.get_columns()
        rng = random.Random(hash(f'{model_name}.{m_id}'))
        mocked = Mocked(model_name)
        for _, column in columns.items():
            if column.primary_key:
                continue
            col_type = column.type
            if col_type == db.types.String:
                setattr(mocked.fields, column.name, self._random_lower(rng, 15))
            if col_type == db.types.Email:
                setattr(mocked.fields, column.name, f'{self._random_lower(rng, 10)}@{self._random_lower(rng, 5)}.com')
            if col_type == db.types.Password:
                setattr(mocked.fields, column.name, (self._random_lower(rng, 10) + str(self._random_int(rng, 1, 100))
                                                     + self._random_symbols(rng, 1)))
            if col_type == db.types.Integer:
                setattr(mocked.fields, column.name, self._random_int(rng, 1, 100))
            if col_type == db.types.Float:
                setattr(mocked.fields, column.name, self._random_int(rng, 1, 100))
            if col_type == db.types.Date:
                setattr(mocked.fields, column.name, self._random_date(rng, datetime.datetime(1900, 1, 1),
                                                                      datetime.datetime(2000, 1, 1)))
        if post_mock_fn and callable(post_mock_fn):
            post_mock_fn(mocked)
        return mocked


mock = Mock()
