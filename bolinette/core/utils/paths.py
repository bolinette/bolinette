import os
import random
import string


def cwd() -> str:
    return os.getcwd()


def random_string(length) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def mkdir(path) -> None:
    os.makedirs(path)


def exists(path) -> bool:
    return os.path.exists(path)


def rename(path, new_path) -> None:
    os.rename(path, new_path)


def join(*args) -> str:
    return os.path.join(*args)


def dirname(path) -> str:
    return os.path.dirname(os.path.realpath(path))


def split(path) -> tuple[str, str]:
    return os.path.split(path)


def rm(path) -> None:
    os.remove(path)


def rm_r(path) -> None:
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(path)


class PathHelper:
    def __init__(self, origin: str) -> None:
        self._origin = origin
        self._cwd = cwd()

    def internal_path(self, *path) -> str:
        return join(self._origin, *path)

    def internal_files_path(self, *path) -> str:
        return join(self._origin, "_files", *path)

    def root_path(self, *path) -> str:
        return join(self._cwd, *path)

    def instance_path(self, *path) -> str:
        return self.root_path("instance", *path)

    def env_path(self, *path) -> str:
        return self.root_path("env", *path)

    def static_path(self, *path) -> str:
        return self.root_path("static", *path)

    def templates_path(self, *path) -> str:
        return self.root_path("templates", *path)
