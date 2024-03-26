class WebSocketSubResult:
    def __init__(self, accepted: bool) -> None:
        self._accepted = accepted

    def __bool__(self) -> bool:
        return self._accepted


class WebSocketSubscription:
    def __init__(self, channel: str) -> None:
        self.channel = channel

    def accept(self) -> WebSocketSubResult:
        return WebSocketSubResult(True)

    def reject(self) -> WebSocketSubResult:
        return WebSocketSubResult(False)
