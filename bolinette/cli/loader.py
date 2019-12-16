from bolinette.cli.nodes import Node, Command, Inline, Ask, Argument, Flag


class Loader:
    @staticmethod
    def load_nodes(nodes):
        _nodes = []
        for node in nodes:
            _nodes.append(Loader.load_node(node))
        return _nodes

    @staticmethod
    def load_node(node):
        _type = node['type']
        if _type == 'node':
            n = Node(node['name'], node.get('desc'))
            n.children = Loader.load_nodes(node['children'])
            return n
        if _type == 'command':
            return Loader.load_command(node)

    @staticmethod
    def load_command(command):
        c = Command(command['name'], command['command'], command.get('desc'),
                    command.get('params', {}), command.get('hidden', False))
        if 'args' in command:
            c.inline = [Loader.load_inline(a) for a in command['args'] if a['type'] == 'inline']
            c.ask = [Loader.load_ask(a) for a in command['args'] if a['type'] == 'ask']
            c.args = [Loader.load_argument(a) for a in command['args'] if a['type'] == 'arg']
            c.flags = [Loader.load_flag(a) for a in command['args'] if a['type'] == 'flag']
        return c

    @staticmethod
    def load_inline(inline):
        return Inline(inline['name'], inline.get('default'), inline.get('desc'))

    @staticmethod
    def load_ask(ask):
        return Ask(ask['name'], ask.get('required', False), ask.get('default'), ask.get('desc'))

    @staticmethod
    def load_argument(arg):
        return Argument(arg['name'], arg['flag'], arg.get('default'), arg.get('desc'))

    @staticmethod
    def load_flag(flag):
        return Flag(flag['name'], flag['flag'], flag.get('desc'))
