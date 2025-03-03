from collections.abc import Awaitable, Callable
from typing import Literal

type Event = Literal["initialized", "started", "stopped", "error"]
type EventListener = Callable[..., Awaitable[None]]
