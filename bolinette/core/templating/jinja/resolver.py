from typing import TYPE_CHECKING

from bolinette.core.exceptions import InitError
from bolinette.core.logging import ArgResolverOptions
from bolinette.core.templating.jinja import JinjaConfig

if TYPE_CHECKING:
    from jinja2 import Environment


class JinjaResolver:
    def __init__(self, config: JinjaConfig) -> None:
        self.config = config
        try:
            from jinja2 import Environment

            self._trigger_types = [Environment]
        except ImportError as err:
            raise InitError("Jinja2 is not installed, install Bolinette with the jinja extra") from err

    def supports(self, options: ArgResolverOptions) -> bool:
        return options.t.cls in self._trigger_types

    def resolve(self, options: ArgResolverOptions) -> "Environment":
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        loader = self.config.loader or FileSystemLoader("templates")
        env = Environment(loader=loader, autoescape=select_autoescape())
        options.injection.add_singleton(Environment, instance=env)
        return env
