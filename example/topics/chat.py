from bolinette import ws

topic = ws.Topic('chat')


@topic.channel(r'.*')
async def receive_message(*, channel, message, **_):
    await topic.send_message([channel], message)
