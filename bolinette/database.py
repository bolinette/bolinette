from sqlalchemy import create_engine, Table, Column, ForeignKey, Integer, String, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref

from bolinette import env
from bolinette.utils import logger


class DatabaseTypes:
    def __init__(self):
        self.Session = sessionmaker()
        self.Model = declarative_base()
        self.Table = Table
        self.Column = Column
        self.Integer = Integer
        self.String = String
        self.Float = Float
        self.Boolean = Boolean
        self.ForeignKey = ForeignKey
        self.relationship = relationship
        self.backref = backref


class Database:
    def __init__(self):
        self.engine = None
        self.session = None
        self.seeders = []
        self.types = DatabaseTypes()

    def init_app(self):
        self.engine = create_engine(self._create_uri(), echo=False)
        self.types.Session.configure(bind=self.engine)
        self.session = self.types.Session()

    def seeder(self, func):
        self.seeders.append(func)
        return func

    async def create_all(self):
        self.types.Model.metadata.create_all(self.engine)

    async def drop_all(self):
        self.types.Model.metadata.drop_all(self.engine)

    async def run_seeders(self):
        for func in self.seeders:
            await func()

    def _create_uri(self):
        dbms = env.get('DBMS', 'SQLITE').lower()
        if dbms == 'sqlite':
            return 'sqlite:///' + env.instance_path(env.get('SQLITE_FILE', f'{env["PROFILE"]}.db'))
        if dbms == 'memory':
            return 'sqlite://'
        if dbms == 'postgresql':
            return 'postgresql://' + env['DB_URL']
        logger.error(f'Unknown database system "{dbms}"')
        exit(1)


db = Database()
