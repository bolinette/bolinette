from bolinette import core, env


class BolinetteContext:
    def __init__(self):
        self.env = env
        self.db = core.DatabaseEngine(self)
