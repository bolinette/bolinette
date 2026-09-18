from collections.abc import Callable
from typing import Any, overload

from escondite import Cache

from bolinette.core.mapping._profiles import Profile
from bolinette.core.mapping._protocol import ObjectProtocol

MAPPING_PROFILE_CACHE_KEY = "__blnt_mapping_profile__"
MAPPING_PROTOCOL_CACHE_KEY = "__blnt_mapping_protocol__"


@overload
def mapping[ProfileT: Profile](cls: type[ProfileT], /, *, cache: Cache | None = None) -> type[ProfileT]: ...
@overload
def mapping[ProfileT: Profile](*, cache: Cache | None = None) -> Callable[[type[ProfileT]], type[ProfileT]]: ...
def mapping(*args: Any, cache: Cache | None = None) -> Any:
    def decorator(cls: type[Profile]) -> type[Profile]:
        Cache.with_fallback(cache).add(MAPPING_PROFILE_CACHE_KEY, cls)
        return cls

    match args:
        case ():
            return decorator
        case (cls,):
            return decorator(cls)
        case _:
            raise TypeError()


@overload
def mapping_protocol[ProtocolT: ObjectProtocol](
    cls: type[ProtocolT], /, *, cache: Cache | None = None
) -> type[ProtocolT]: ...
@overload
def mapping_protocol[ProtocolT: ObjectProtocol](
    *, cache: Cache | None = None
) -> Callable[[type[ProtocolT]], type[ProtocolT]]: ...
def mapping_protocol(*args: Any, cache: Cache | None = None) -> Any:
    def decorator(cls: type[ObjectProtocol]) -> type[ObjectProtocol]:
        Cache.with_fallback(cache).add(MAPPING_PROTOCOL_CACHE_KEY, cls)
        return cls

    match args:
        case ():
            return decorator
        case (cls,):
            return decorator(cls)
        case _:
            raise TypeError()
