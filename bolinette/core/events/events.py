from collections.abc import Awaitable, Callable

type EventListener = Callable[..., Awaitable[None]]

BLNT_INITIALIZED_EVENT = "blnt:life:initialized"
BLNT_STARTED_EVENT = "blnt:life:started"
BLNT_STOPPED_EVENT = "blnt:life:stopped"
BLNT_ERROR_EVENT = "blnt:life:error"
