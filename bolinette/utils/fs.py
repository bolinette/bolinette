import os


def read_version(path):
    try:
        with open(join(path, '.version')) as f:
            for line in f:
                return line.strip().replace('\n', '')
    except FileNotFoundError:
        return None


def read_requirements(path):
    try:
        with open(join(path, 'requirements.txt')) as f:
            return filter(lambda r: len(r), f.read().split('\n'))
    except FileNotFoundError:
        return []


def read_file(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return None


def cwd():
    return os.getcwd()


def dirname(path):
    return os.path.dirname(os.path.realpath(path))


def join(*args):
    return os.path.join(*args)


def mkdir(path):
    os.makedirs(path)


def exists(path):
    return os.path.exists(path)


def delete(path):
    os.unlink(path)
