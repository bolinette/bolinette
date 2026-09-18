from bolinette.core.exceptions import BolinetteError


class CommandError(BolinetteError):
    def __init__(self, message: str, *, code: int) -> None:
        BolinetteError.__init__(self, message)
        self.code = code


class CommandHelpError(CommandError):
    def __init__(self, message: str, *, code: int = 1) -> None:
        CommandError.__init__(self, message, code=code)


class CommandUsageError(CommandError):
    def __init__(self, message: str, *, code: int = 2) -> None:
        CommandError.__init__(self, message, code=code)
