import os
import random
import string


def cwd():
    return os.getcwd()


def random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def mkdir(path):
    os.makedirs(path)


def exists(path):
    return os.path.exists(path)


def rename(path, new_path):
    os.rename(path, new_path)


def join(*args):
    return os.path.join(*args)


def dirname(path):
    return os.path.dirname(os.path.realpath(path))


def split(path):
    return os.path.split(path)


def delete(path):
    os.unlink(path)
