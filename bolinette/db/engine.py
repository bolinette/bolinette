from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from bolinette import env, db
from bolinette.utils import logger


class Engine:
    def __init__(self):
        self.engine = None
        self.session = None
        self.seeders = []
        self.Session = None
        self.model = None

    def init_app(self):
        self.engine = create_engine(self._create_uri(), echo=False)
        self.Session = sessionmaker()
        self.model = declarative_base()
        self.Session.configure(bind=self.engine)
        self.session = self.Session()
        db.models.init_models()

    def seeder(self, func):
        self.seeders.append(func)
        return func

    async def create_all(self):
        self.model.metadata.create_all(self.engine)

    async def drop_all(self):
        self.model.metadata.drop_all(self.engine)

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


engine = Engine()
