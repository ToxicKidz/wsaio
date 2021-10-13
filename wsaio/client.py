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

        self._opened = False
        self._closing = False

    def is_opened(self):
        return self._opened

    async def _open_hook(self):
        self._opened = True
        await self.on_open()

    async def _ping_hook(self, data):
        await self.pong(data)
        await self.on_ping(data)

    async def _close_hook(self, code, data):
        if not self._closing:
            await self.close(code=code)

        self.stream.close()
        self._opened = False

        await self.on_close(code, data)

    async def _error_hook(self, exc):
        if not self.is_opened():
            raise exc

        if isinstance(exc, InvalidFrameError):
            await self.close(exc.message, code=exc.code)
        else:
            self.stream.close()

    async def on_open(self):
        pass

    async def on_ping(self, data):
        pass

    async def on_pong(self, data):
        pass

    async def on_text(self, data):
        pass

    async def on_binary(self, data):
        pass

    async def on_close(self, code, data):
        pass

    async def ping(self, data=None):
        if not self.is_opened():
            raise RuntimeError('The WebSocket is not opened')

        await self.writer.ping(data, mask=True)

    async def pong(self, data=None):
        if not self.is_opened():
            raise RuntimeError('The WebSocket is not opened')

        await self.writer.pong(data, mask=True)

    async def write(self, data, *, binary=False):
        if not self.is_opened():
            raise RuntimeError('The WebSocket is not opened')

        await self.writer.write(data, binary=binary, mask=True)

    async def close(self, data=None, *, code=wsframe.WS_NORMAL_CLOSURE):
        if not self.is_opened():
            raise RuntimeError('The WebSocket is not opened')

        if self._closing:
            raise RuntimeError('The WebSocket cannot be closed more than once')

        self._closing = True
        await self.writer.close(data, code=code, mask=True)

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

            self.reader._on_ping = self._ping_hook
            self.reader._on_pong = self.on_pong
            self.reader._on_text = self.on_text
            self.reader._on_binary = self.on_binary
            self.reader._on_close = self._close_hook

            self.loop.create_task(self._open_hook())

            self.stream.set_error_handler(self._error_hook)
            self.stream.set_parser(self.reader.read_frame)

    async def wait_until_closed(self):
        await self.stream.wait_until_closed()
