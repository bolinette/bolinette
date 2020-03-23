import os


def cwd():
    return os.getcwd()


def dirname(path):
    return os.path.dirname(os.path.realpath(path))


def join(*args):
    return os.path.join(*args)
