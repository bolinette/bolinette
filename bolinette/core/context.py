from bolinette.core.utils import paths, files


class Context:
    def __init__(self, origin: str):
        self._origin = origin
        self._cwd = paths.cwd()
        self.manifest = (
            files.read_manifest(
                self.root_path(), params={"version": "0.0.0"}
            )
            or {}
        )

    def internal_path(self, *path):
        return paths.join(self._origin, *path)

    def internal_files_path(self, *path):
        return paths.join(self._origin, "_files", *path)

    def root_path(self, *path):
        return paths.join(self._cwd, *path)

    def instance_path(self, *path):
        return self.root_path("instance", *path)

    def env_path(self, *path):
        return self.root_path("env", *path)

    def static_path(self, *path):
        return self.root_path("static", *path)

    def templates_path(self, *path):
        return self.root_path("templates", *path)
