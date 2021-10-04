import asyncio
from http import HTTPStatus
from urllib.parse import urlparse

from .import headers as httphdrs
from .exceptions import HandshakeFailureError
from .stream import Stream
from .util import genacckey, genseckey

SWITCHING_PROTOCOLS = HTTPStatus.SWITCHING_PROTOCOLS


class WebSocketHandshake:
    def __init__(self, urlinfo, *,  stream):
        self.host, self.port, self.path, self.query = urlinfo

        self.stream = stream
        self.stream.set_parser(self.parse_response)

        self._future = self.stream.loop.create_future()

    @classmethod
    async def from_url(cls, url, *, loop, **kwargs):
        result = urlparse(url)

        if result.scheme not in ('ws', 'wss'):
            raise ValueError(f'Invalid url scheme for WebSocket {url.scheme}')

        host = result.hostname

        if not result.port:
            if result.scheme == 'wss':
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

        if not result.query:
            query = ''
        else:
            query = f'?{result.query}'

        stream = Stream(loop=loop)
        await stream.create_protocol(host, port, **kwargs)

        return cls((host, port, path, query), stream=stream)

    def parse_response(self, ctx):
        status = None
        headers = httphdrs.HTTPHeaders()

        buffer = ctx.get_buffer()
        start = 0

        while True:
            try:
                index = buffer.index(b'\r\n', start)
            except ValueError:
                yield from ctx.fill()
            else:
                if status is None:
                    status = buffer[start:index].decode('utf-8')
                else:
                    key, value = buffer[start:index].split(b':', 1)
                    key = key.strip().decode('utf-8')
                    value = value.strip().decode('utf-8')

                    headers[key] = value

                start = index + 2

                if buffer[index + 2:index + 4] == b'\r\n':
                    del buffer[:index + 4]
                    break

        self._future.set_result((headers, status.split(' ', 2)))

        ctx.reset_parser()

    async def negotiate(self, *, timeout):
        seckey = genseckey()
        acckey = genacckey(seckey.encode('utf-8'))

        headers = httphdrs.HTTPHeaders()

        headers[httphdrs.HOST] = f'{self.host}:{self.port}'
        headers[httphdrs.CONNECTION] = 'Upgrade'
        headers[httphdrs.UPGRADE] = 'websocket'
        headers[httphdrs.SEC_WEBSOCKET_KEY] = seckey
        headers[httphdrs.SEC_WEBSOCKET_VERSION] = '13'

        self.stream.write(f'GET {self.path}{self.query} HTTP/1.1\r\n')

        for key, values in headers.items():
            for value in values:
                self.stream.write(f'{key}: {value}\r\n')

        self.stream.write('\r\n')

        try:
            headers, (version, code, _) = await asyncio.wait_for(self._future, timeout=timeout)
        except asyncio.TimeoutError:
            raise HandshakeFailureError(
                'The handshake timed out while waiting for response'
            ) from None

        if version != 'HTTP/1.1':
            raise HandshakeFailureError(f'Expected HTTP/1.1, got {version}')

        if code != str(SWITCHING_PROTOCOLS.value):
            raise HandshakeFailureError(f'Expected status code 101, got {code}')

        if headers.getone(httphdrs.CONNECTION).lower() != 'upgrade':
            raise HandshakeFailureError(f'The {httphdrs.CONNECTION!r} header is not \'upgrade\'')

        if headers.getone(httphdrs.UPGRADE).lower() != 'websocket':
            raise HandshakeFailureError(f'The {httphdrs.UPGRADE!r} header is not \'websocket\'')

        if headers.getone(httphdrs.SEC_WEBSOCKET_ACCEPT) != acckey:
            raise HandshakeFailureError(
                f'The {httphdrs.SEC_WEBSOCKET_ACCEPT!r} header does not match the secret key'
            )

        return self.stream

    def shutdown(self):
        self.stream.close()
