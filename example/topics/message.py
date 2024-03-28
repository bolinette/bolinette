from bolinette.web.ws import (
    WebSocketContext,
    WebSocketMessage,
    WebSocketSubResult,
    WebSocketSubscription,
    channel,
    topic,
)
from example.services import UserService


@topic("message")
class MessageTopic:
    def __init__(self, ctx: WebSocketContext, user_service: UserService) -> None:
        self.ctx = ctx
        self.user_service = user_service

    async def subscribe(self, sub: WebSocketSubscription) -> WebSocketSubResult:
        return sub.accept()

    @channel("to:.*")
    async def receive_message(self, message: WebSocketMessage[str]) -> None:
        await self.ctx.send("message", message.channel, message.value)
