class Flag:
    def __init__(self, name, flag, desc):
        self.name = name
        self.flag = flag
        self.value = False
        self.desc = desc

    def __repr__(self):
        return f'<Flag {self.name}>'
