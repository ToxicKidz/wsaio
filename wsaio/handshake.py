from http import HTTPStatus
from urllib.parse import urlparse

from .import headers as httphdrs
from .stream import Stream
from .util import genacckey, genseckey

SWITCHING_PROTOCOLS = HTTPStatus.SWITCHING_PROTOCOLS


class WebSocketHandshake:
    def __init__(self, urlinfo, *,  stream):
        self.host, self.port, self.path, self.params = urlinfo

        self.stream = stream
        self.stream.set_parser(self.parse_response)

    @classmethod
    async def create_connection(cls, url, *, loop, **kwargs):
        result = urlparse(url)

        if result.scheme not in ('ws', 'wss'):
            raise ValueError(f'Invalid url scheme for WebSocket {url.scheme}')

        host = result.hostname

        if not result.port:
            if url.scheme == 'wss':
                port = 443
                kwargs.setdefault('ssl', True)
            else:
                port = 80
        else:
            port = result.port

        if not result.path:
            path = '/'
        else:
            path = result.path

        stream = Stream(loop=loop)
        await stream.create_protocol(host, port, **kwargs)

        return cls((host, port, path, result.params), stream=stream)

    async def send_request(self):
        self.seckey = genseckey()
        self.acckey = genacckey(self.seckey)

        headers = httphdrs.HTTPHeaders()

        headers[httphdrs.HOST] = f'{self.host}:{self.port}'
        headers[httphdrs.CONNECTION] = 'Upgrade'
        headers[httphdrs.UPGRADE] = 'websocket'
        headers[httphdrs.SEC_WEBSOCKET_KEY] = self.seckey

        self.stream.write(f'HTTP/1.1 {SWITCHING_PROTOCOLS.value} {SWITCHING_PROTOCOLS.phrase}')

        for key, value in headers.items():
            self.stream.write(f'{key}: {value}\r\n')

        self.stream.write('\r\n')

    def parse_response(self, ctx):
        status = None
        headers = httphdrs.HTTPHeaders()

        buffer = ctx.get_buffer()
        start = 0

        while True:
            yield from ctx.fill()

            try:
                index = buffer.index('\r\n', start)
            except ValueError:
                continue
            else:
                if buffer[index:index + 2] == '\r\n':
                    del buffer[index + 2:]
                    break

                if status is None:
                    status = buffer[start:index]
                else:
                    key, value = buffer[start:index].split(b':', 1)
                    key = key.strip().decode('utf-8')
                    value = value.strip().decode('utf-8')

                    headers[key] = value

                start = index + 2
