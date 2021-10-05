import asyncio

from . import frame as wsframe
from .exceptions import HandshakeFailureError, InvalidFrameError
from .handshake import WebSocketHandshake
from .reader import WebSocketReader
from .writer import WebSocketWriter


class WebSocketClient:
    def __init__(self, *, loop=None):
        if loop is not None:
            self.loop = loop
        else:
            self.loop = asyncio.get_event_loop()

        self.stream = None
        self.reader = None
        self.writer = None

        self._sent_close = False

    async def on_open(self):
        pass

    async def _on_ping(self, data):
        await self.pong(data)
        await self.on_ping(data)

    async def on_ping(self, data):
        pass

    async def on_pong(self, data):
        pass

    async def on_text(self, data):
        pass

    async def on_binary(self, data):
        pass

    async def _on_close(self, code, data):
        if not self._sent_close:
            await self.close(code=code)

        self.stream.close()

        await self.on_close(code, data)

    async def on_close(self, code, data):
        pass

    async def ping(self, data=None):
        await self.writer.ping(data, mask=True)

    async def pong(self, data=None):
        await self.writer.pong(data, mask=True)

    async def close(self, data=None, *, code=wsframe.WS_NORMAL_CLOSURE):
        self._sent_close = True
        await self.writer.close(data, code=code, mask=True)

    async def write(self, data, *, binary=False):
        await self.writer.write(data, binary=binary, mask=True)

    async def _error_handler(self, exc):
        if isinstance(exc, InvalidFrameError):
            await self.close(exc.message, code=exc.code)

    async def connect(self, url, *, timeout=30, **kwargs):
        handshake = await WebSocketHandshake.from_url(url, loop=self.loop, **kwargs)

        try:
            self.stream = await handshake.negotiate(timeout=timeout)
        except HandshakeFailureError:
            handshake.shutdown()
            raise
        else:
            self.reader = WebSocketReader(stream=self.stream)
            self.writer = WebSocketWriter(stream=self.stream)

            self.reader._on_ping = self._on_ping
            self.reader._on_pong = self.on_pong
            self.reader._on_text = self.on_text
            self.reader._on_binary = self.on_binary
            self.reader._on_close = self._on_close

            self.loop.create_task(self.on_open())

            self.stream.set_error_handler(self._error_handler)
            self.stream.set_parser(self.reader.read_frame)

    async def wait_until_closed(self):
        await self.stream.wait_until_closed()
