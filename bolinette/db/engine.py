from sqlalchemy import create_engine

from bolinette import env, db
from bolinette.utils import logger


class Engine:
    def __init__(self):
        self.engine = None
        self.session = None
        self.seeders = []

    def init_app(self):
        self.engine = create_engine(self._create_uri(), echo=False)
        db.defs.Session.configure(bind=self.engine)
        self.session = db.defs.Session()

    def seeder(self, func):
        self.seeders.append(func)
        return func

    async def create_all(self):
        db.defs.model.metadata.create_all(self.engine)

    async def drop_all(self):
        db.defs.model.metadata.drop_all(self.engine)

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
