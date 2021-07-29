class BolinetteExtension:
    def __init__(self, name: str, dependencies: list['BolinetteExtension'] = None):
        self.name = name
        self.dependencies = dependencies or []

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return (isinstance(other, BolinetteExtension) and self.name == other.name
                or isinstance(other, str) and self.name == other)

    def __repr__(self):
        return f'<Extensions {self.name}>'


class Extensions:
    MODELS = BolinetteExtension('models')
    WEB = BolinetteExtension('web', [MODELS])
    SOCKETS = BolinetteExtension('sockets', [MODELS])
    ALL = BolinetteExtension('all')
