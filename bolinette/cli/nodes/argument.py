class Argument:
    def __init__(self, name, flag, default, desc):
        self.name = name
        self.flag = flag
        self.default = default
        self.value = default
        self.missing = False
        self.desc = desc

    def __repr__(self):
        return f'<Argument {self.name}>'
