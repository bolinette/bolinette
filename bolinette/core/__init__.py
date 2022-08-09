from bolinette.core.version import __version__
from bolinette.core.objects import CoreSection, GenericMeta
from bolinette.core.metadata import meta
from bolinette.core.cache import (
    InjectionStrategy,
    Cache,
    __core_cache__,
    init_func,
    injectable,
)
from bolinette.core.inject import Injection, init_method, require
from bolinette.core.logger import Logger, ConsoleColorCode
from bolinette.core.environment import Environment, environment
from bolinette.core.command import command
from bolinette.core.bolinette import Bolinette, main_func
