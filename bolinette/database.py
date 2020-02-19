import os
from functools import wraps

from flask_sqlalchemy import SQLAlchemy
from bolinette_cli import logger

from bolinette import env

_seeder_funcs = []

db = SQLAlchemy()


def create_db_uri():
    dbms = env.get('DBMS', 'SQLITE').lower()
    if dbms == 'sqlite':
        return 'sqlite:///' + env.instance_path(env.get('SQLITE_FILE', f'{env["PROFILE"]}.db'))
    if dbms == 'memory':
        return 'sqlite://'
    if dbms == 'postgresql':
        return 'postgresql://' + env['DB_URL']
    logger.error(f'Unknown database system "{dbms}"')
    exit(1)


def init_db(bolinette):
    bolinette.app.config['SQLALCHEMY_DATABASE_URI'] = create_db_uri()
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
