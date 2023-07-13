import os


class PathUtils:
    def __init__(self) -> None:
        self._cwd = self.cwd()

    def root_path(self, *path: str) -> str:
        return self.join(self._cwd, *path)

    def instance_path(self, *path: str) -> str:
        return self.root_path("instance", *path)

    def env_path(self, *path: str) -> str:
        return self.root_path("env", *path)

    def static_path(self, *path: str) -> str:
        return self.root_path("static", *path)

    def templates_path(self, *path: str) -> str:
        return self.root_path("templates", *path)

    @staticmethod
    def cwd() -> str:
        return os.getcwd()

    @staticmethod
    def mkdir(path: str) -> None:
        os.makedirs(path)

    @staticmethod
    def exists(path: str) -> bool:
        return os.path.exists(path)

    @staticmethod
    def rename(path: str, new_path: str) -> None:
        os.rename(path, new_path)

    @staticmethod
    def join(*args: str) -> str:
        return os.path.join(*args)

    @staticmethod
    def dirname(path: str) -> str:
        return os.path.dirname(os.path.realpath(path))

    @staticmethod
    def split(path: str) -> tuple[str, str]:
        return os.path.split(path)

    @staticmethod
    def rm(path: str, *, recursive: bool = False) -> None:
        if recursive:
            for root, dirs, files in os.walk(path, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(path)
        else:
            os.remove(path)
