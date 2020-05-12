from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from bolinette import core
from bolinette.utils import logger


class DatabaseEngine:
    def __init__(self, context: 'core.BolinetteContext'):
        self.engine = create_engine(self._create_uri(context), echo=False)
        self.Session = sessionmaker()
        self.model = declarative_base()
        self.Session.configure(bind=self.engine)
        self.session = self.Session()

    async def create_all(self):
        self.model.metadata.create_all(self.engine)

    async def drop_all(self):
        self.model.metadata.drop_all(self.engine)

    def _create_uri(self, context: 'core.BolinetteContext'):
        dbms = context.env.get('DBMS', 'SQLITE').lower()
        if dbms == 'sqlite':
            return 'sqlite:///' + context.env.instance_path(
                context.env.get('SQLITE_FILE', f'{context.env["PROFILE"]}.db'))
        if dbms == 'memory':
            return 'sqlite://'
        if dbms == 'postgresql':
            return 'postgresql://' + context.env['DB_URL']
        logger.error(f'Unknown database system "{dbms}"')
        exit(1)

    async def run_seeders(self, context: 'core.BolinetteContext'):
        for func in core.cache.seeders:
            await func(context)
