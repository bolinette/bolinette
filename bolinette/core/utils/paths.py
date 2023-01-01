import os
import random
import string

from bolinette.core import injectable, __core_cache__


@injectable(strategy="singleton", cache=__core_cache__)
class PathUtils:
    def __init__(self) -> None:
        self._cwd = self.cwd()

    def root_path(self, *path) -> str:
        return self.join(self._cwd, *path)

    def instance_path(self, *path) -> str:
        return self.root_path("instance", *path)

    def env_path(self, *path) -> str:
        return self.root_path("env", *path)

    def static_path(self, *path) -> str:
        return self.root_path("static", *path)

    def templates_path(self, *path) -> str:
        return self.root_path("templates", *path)

    @staticmethod
    def cwd() -> str:
        return os.getcwd()

    @staticmethod
    def random_string(length) -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    @staticmethod
    def mkdir(path) -> None:
        os.makedirs(path)

    @staticmethod
    def exists(path) -> bool:
        return os.path.exists(path)

    @staticmethod
    def rename(path, new_path) -> None:
        os.rename(path, new_path)

    @staticmethod
    def join(*args) -> str:
        return os.path.join(*args)

    @staticmethod
    def dirname(path) -> str:
        return os.path.dirname(os.path.realpath(path))

    @staticmethod
    def split(path) -> tuple[str, str]:
        return os.path.split(path)

    @staticmethod
    def rm(path, *, recursive=False) -> None:
        if recursive:
            for root, dirs, files in os.walk(path, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(path)
        else:
            os.remove(path)
