import random
import string

from bolinette import db
from bolinette.marshalling import get_payload, types


def _random_lower(rng, length):
    return ''.join(rng.choices(string.ascii_lowercase, k=length))


def _random_symbols(rng, length):
    return ''.join(rng.choices(string.punctuation, k=length))


def _random_int(rng, a, b):
    return rng.randint(a, b)


def create_mock(m_id, model, key='default'):
    rng = random.Random(hash(f'{model}.{key}.{m_id}'))
    definition = get_payload(f'{model}.{key}')
    mock = {}
    for field in definition.fields:
        if isinstance(field.type, types.classes.String):
            mock[field.name] = _random_lower(rng, 15)
        elif isinstance(field.type, types.classes.Email):
            mock[field.name] = f'{_random_lower(rng, 10)}@{_random_lower(rng, 5)}.com'
        elif isinstance(field.type, types.classes.Password):
            mock[field.name] = (_random_lower(rng, 10) + str(_random_int(rng, 1, 100)) +
                                _random_symbols(rng, 1))
        elif isinstance(field.type, types.classes.Integer):
            mock[field.name] = _random_int(rng, 1, 100)
    return mock


def insert(model, mock):
    entity = model(**mock)
    db.session.add(entity)
    db.session.commit()
    return mock
