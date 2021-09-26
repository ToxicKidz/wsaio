class InvalidDataError(Exception):
    pass


class InvalidFrameError(InvalidDataError):
    def __init__(self, message, code):
        self.message = message
        self.code = code
