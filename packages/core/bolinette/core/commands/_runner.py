from soupape import AsyncInjector

from bolinette.core.commands import CommandParser
from bolinette.core.commands._meta import ParsedParams, RunnableCommand


def _make_params_resolver(cmd: RunnableCommand):
    def _resolve_params() -> ParsedParams:
        return ParsedParams({**cmd.args})

    return _resolve_params


class CommandRunner:
    def __init__(self, injector: AsyncInjector, parser: CommandParser) -> None:
        self._injector = injector
        self._parser = parser

    def parse(self, args: list[str]) -> RunnableCommand:
        return self._parser.parse_command(args)

    async def run(self, cmd: RunnableCommand) -> int | None:
        async with self._injector.get_scoped_injector() as scope:
            scope.services.add_scoped(_make_params_resolver(cmd))
            return await scope.call(cmd.func)
