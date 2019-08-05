
import os

from flask_sqlalchemy import SQLAlchemy

from bolinette import env, logger

db = SQLAlchemy()


def create_db_uri(_app):
    dbms = env.get('DBMS', 'SQLITE').lower()
    if dbms == 'sqlite':
        return 'sqlite:///' + os.path.join(_app.instance_path,
                                           env.get('SQLITE_FILE', f'database.{_app.env}.db'))
    if dbms == 'memory':
        return 'sqlite://'
    logger.error(f'Unknown database system "{dbms}"')
    exit(1)


def init_db(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = create_db_uri(app)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    db.init_app(app)
