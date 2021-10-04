from reprlib import recursive_repr

HOST = 'Host'
UPGRADE = 'Upgrade'
CONNECTION = 'Connection'
SEC_WEBSOCKET_KEY = 'Sec-WebSocket-Key'
SEC_WEBSOCKET_ACCEPT = 'Sec-WebSocket-Accept'
SEC_WEBSOCKET_VERSION = 'Sec-WebSocket-Version'


class HTTPHeaders:
    def __init__(self):
        self.__dict = {}

    @recursive_repr('HTTPHeaders({...})')
    def __repr__(self):
        return f'HTTPHeaders({self.__dict})'

    def __set_default(self, key):
        key = key.lower()
        header = self.__dict.get(key)

        if header is None:
            header = self.__dict[key] = []

        return header

    def __getitem__(self, key):
        return self.__dict[key.lower()]

    def __setitem__(self, key, value):
        header = self.__set_default(key)
        header.append(value)

    def __delitem__(self, key):
        del self.__dict[key.lower()]

    def keys(self):
        return self.__dict.keys()

    def value(self):
        return self.__dict.values()

    def items(self):
        return self.__dict.items()

    def get(self, key, default=None):
        return self.__dict.get(key.lower(), default)

    def getone(self, key, default=''):
        return self.get(key, (default,))[0]
