from bolinette import ws

t = ws.Topic('user', login_required=True)


@t.subscribe
def user_topic_sub(topic, response, *, current_user, **_):
    topic.subscriptions[current_user.username] = [response]
