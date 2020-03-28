class Commands:
    def __init__(self):
        self.commands = {}

    def register(self, name, func):
        self.commands[name] = func


commands = Commands()


def command(name):
    def inner(func):
        commands.register(name, func)
        return func

    return inner
