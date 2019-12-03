class Ask:
    def __init__(self, name, required, default, desc):
        self.name = name
        self.required = required
        self.default = default
        self.value = default
        self.desc = desc

    def __repr__(self):
        return f'<Ask {self.name}>'
