class Node:
    def __init__(self, name, desc):
        self.name = name
        self.children = []
        self.desc = desc

    def __repr__(self):
        return f'<Node {self.name}>'
