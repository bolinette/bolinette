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


def rm(path):
    os.remove(path)


def rm_r(path):
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(path)
