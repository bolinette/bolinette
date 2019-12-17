import os
from functools import wraps

from flask_sqlalchemy import SQLAlchemy

from bolinette import env, logger

_seeder_funcs = []

db = SQLAlchemy()


def create_db_uri(_app):
    dbms = env.get('DBMS', 'SQLITE').lower()
    if dbms == 'sqlite':
        return 'sqlite:///' + os.path.join(_app.instance_path,
                                           env.get('SQLITE_FILE', f'{_app.env}.db'))
    if dbms == 'memory':
        return 'sqlite://'
    logger.error(f'Unknown database system "{dbms}"')
    exit(1)


def init_db(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = create_db_uri(app)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    db.init_app(app)


def seeder(func):
    _seeder_funcs.append(func)

    @wraps(func)
    def inner(*args, **kwargs):
        func(*args, **kwargs)

    return inner


def run_seeders():
    for func in _seeder_funcs:
        func()
