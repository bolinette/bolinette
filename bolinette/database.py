import os
from functools import wraps

from flask_sqlalchemy import SQLAlchemy

from bolinette import env, logger

_seeder_funcs = []

db = SQLAlchemy()


def create_db_uri(bolinette):
    dbms = env.get('DBMS', 'SQLITE').lower()
    if dbms == 'sqlite':
        return 'sqlite:///' + bolinette.instance_path(env.get('SQLITE_FILE', f'{bolinette.app.env}.db'))
    if dbms == 'memory':
        return 'sqlite://'
    logger.error(f'Unknown database system "{dbms}"')
    exit(1)


def init_db(bolinette):
    bolinette.app.config['SQLALCHEMY_DATABASE_URI'] = create_db_uri(bolinette)
    bolinette.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    db.init_app(bolinette.app)


def seeder(func):
    _seeder_funcs.append(func)

    @wraps(func)
    def inner(*args, **kwargs):
        func(*args, **kwargs)

    return inner


def run_seeders():
    for func in _seeder_funcs:
        func()
