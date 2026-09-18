import inspect
from collections.abc import Awaitable, Mapping
from dataclasses import dataclass
from functools import cached_property
from typing import Any, ClassVar, override

from peritype import FWrap, TWrap
from soupape.extension import AnnotatedResolutionFunction, ResolutionContext

from bolinette.core.exceptions import InitError


@dataclass(slots=True, frozen=True)
class CommandMeta:
    KEY: ClassVar[str] = "__blnt_cmd_meta__"

    path: str
    summary: str
    run_startup: bool


@dataclass(slots=True, frozen=True)
class ParsedParams:
    params: dict[str, Any]


class CommandParam(AnnotatedResolutionFunction):
    def __init__(self, *, default: Any | None = None, summary: str | None = None) -> None:
        self.default = default
        self.summary = summary

    @override
    def __resolve__(self, context: ResolutionContext, params: ParsedParams) -> Any:
        if context.caller_context is None:  # pragma: no cover
            raise TypeError("A command parameter can only resolve a function parameter")
        return params.params[context.caller_context.param_name]


class CommandArg(CommandParam):
    pass


class CommandOption(CommandParam):
    def __init__(
        self,
        shorthand: str | None = None,
        /,
        *,
        default: Any | None = None,
        summary: str | None = None,
    ) -> None:
        CommandParam.__init__(self, default=default, summary=summary)
        self.shorthand = shorthand


class Command:
    def __init__(self, func: FWrap[..., Awaitable[None]], run_startup: bool) -> None:
        self._func = func
        self._run_startup = run_startup

    @property
    def run_startup(self) -> bool:
        return self._run_startup

    @property
    def func(self) -> FWrap[..., Any]:
        return self._func

    @cached_property
    def signature_hints(self) -> dict[str, TWrap[Any]]:
        return self._func.get_signature_hints()

    @cached_property
    def signature_parameters(self) -> dict[str, inspect.Parameter]:
        return {**self._func.signature.parameters}

    @cached_property
    def signature_cmd_params(self) -> dict[str, CommandParam]:
        params: dict[str, CommandParam] = {}
        for p_name, hint in self.signature_hints.items():
            for anno in hint.annotations:
                if anno is CommandArg or anno is CommandOption:
                    raise InitError(
                        f"Command {self._func}, parameter '{p_name}', annotate with {anno.__name__}() "
                        "instead of the bare class"
                    )
                if isinstance(anno, CommandParam):
                    params[p_name] = anno
                    break
        return params


class RunnableCommand(Command):
    def __init__(self, origin: Command, args: dict[str, Any]) -> None:
        Command.__init__(self, origin.func, origin.run_startup)
        self._args = args

    @property
    def args(self) -> Mapping[str, Any]:
        return self._args
