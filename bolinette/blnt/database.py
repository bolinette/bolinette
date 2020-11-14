from bolinette.utils import logger
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from bolinette import blnt


class DatabaseEngine:
    def __init__(self, context: 'blnt.BolinetteContext'):
        self.engine = create_engine(self._create_uri(context), echo=False)
        self.Session = sessionmaker()
        self.model = declarative_base()
        self.Session.configure(bind=self.engine)
        self.session = self.Session()

    async def create_all(self):
        self.model.metadata.create_all(self.engine)

    async def drop_all(self):
        self.model.metadata.drop_all(self.engine)

    def _create_uri(self, context: 'blnt.BolinetteContext'):
        dbms = context.env.get('dbms', 'sqlite').lower()
        if dbms == 'sqlite':
            return 'sqlite:///' + context.instance_path(
                context.env.get('sqlite_file', f'{context.env["profile"]}.db'))
        if dbms == 'memory':
            return 'sqlite://'
        if dbms == 'postgresql':
            return 'postgresql://' + context.env['db_url']
        logger.error(f'Unknown database system "{dbms}"')
        exit(1)

    async def run_seeders(self, context: 'blnt.BolinetteContext'):
        for func in blnt.cache.seeders:
            await func(context)
