class Command:
    def __init__(self, name, command, desc, params, hidden):
        self.name = name
        self.command = command
        self.inline = []
        self.ask = []
        self.args = []
        self.flags = []
        self.desc = desc
        self.params = params
        self.hidden = hidden

    def __repr__(self):
        return f'<Command {self.name}>'
