from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Sequence

from escondite import Cache
from soupape import ServiceCollection

type NewProjectHook = Callable[..., Awaitable[None]]


class Extension(ABC):
    name: str
    dependencies: Sequence[type["Extension"]] = ()

    @abstractmethod
    def register_services(self, services: ServiceCollection, cache: Cache) -> None: ...

    def get_new_project_hooks(self) -> Sequence[NewProjectHook]:
        return ()


class LoadedExtensions:
    def __init__(self, extensions: Sequence[Extension]) -> None:
        self._extensions = tuple(extensions)

    def __iter__(self):
        return iter(self._extensions)

    def __len__(self) -> int:
        return len(self._extensions)

    def get[ExtT: Extension](self, ext_type: type[ExtT]) -> ExtT:
        for ext in self._extensions:
            if isinstance(ext, ext_type):
                return ext
        raise KeyError(ext_type.__qualname__)
