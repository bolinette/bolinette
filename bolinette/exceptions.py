class APIError(Exception):
    def __init__(self, name, function, messages):
        super().__init__(name)
        self.function = function
        self.messages = messages

    def __str__(self):
        return ", ".join(self.messages)

    @property
    def response(self):
        return self.function(self.messages)


class InternalError(Exception):
    def __init__(self, message):
        super().__init__('InternalError')
        self.message = message


class AbortRequestException(Exception):
    def __init__(self, resp):
        self.response = resp
