class Inline:
    def __init__(self, name, default, desc):
        self.name = name
        self.default = default
        self.value = default
        self.desc = desc

    def __repr__(self):
        return f'<Inline {self.name}>'
