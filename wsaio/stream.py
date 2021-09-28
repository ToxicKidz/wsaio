import asyncio

from .util import getbytes


class StreamProtocol(asyncio.Protocol):
    def __init__(self, stream):
        self.loop = stream.loop
        self.transport = None

        self._stream = stream
        self._stream.set_protocol(self)

        self._over_ssl = False

        self._paused = False
        self._connection_lost = False
        self._drain_waiter = None

        self._close_waiter = self.loop.create_future()

    def connection_made(self, transport):
        self.transport = transport
        self._over_ssl = transport.get_extra_info('sslcontext') is not None

    def pause_writing(self):
        assert not self._paused
        self._paused = True

    def resume_writing(self):
        assert self._paused
        self._paused = False

        if self._drain_waiter is not None:
            if not self._drain_waiter.done():
                self._drain_waiter.set_result(None)

            self._drain_waiter = None

    def data_received(self, data):
        self._stream.feed_data(data)

    def eof_received(self):
        self._stream.feed_eof()
        if self._over_ssl:
            return False
        return True

    def connection_lost(self, exc):
        self._connection_lost = True

        if self._paused and self._drain_waiter is not None:
            if not self._drain_waiter.done():
                if exc is not None:
                    self._drain_waiter.set_exception(exc)
                else:
                    self._drain_waiter.set_result(None)

        if not self._close_waiter.done():
            if exc is not None:
                self._close_waiter.set_exception(exc)
            else:
                self._close_waiter.set_result(None)

        self.transport = None

    async def wait_until_drained(self):
        if self._connection_lost:
            raise ConnectionResetError('Connection lost')

        if self._paused:
            assert self._drain_waiter is None or self._drain_waiter.cancelled()

            self._drain_waiter = self.loop.create_future()
            await self._drain_waiter

    async def wait_until_closed(self):
        await self._close_waiter


class StreamParserContext:
    def __init__(self, stream):
        self.stream = stream

        self._parsefunc = None
        self._parser = None

        self._buffer = bytearray()

    def set_parser(self, func):
        self._parsefunc = func

    def read(self, amount):
        while len(self._buffer) < amount:
            data = yield
            self._buffer.extend(data)

        data = bytes(self._buffer[:amount])
        del self._buffer[:amount]

        return data

    def feed_data(self, data):
        while True:
            if self._parser is None:
                self._parser = self._parsefunc(self)
                self._parser.send(None)

            try:
                self._parser.send(data)
            except StopIteration:
                self._parser = None
            else:
                break

    def feed_eof(self):
        pass


class Stream:
    def __init__(self, loop):
        self.loop = loop
        self.protocol = None

        self._ctx = StreamParserContext(self)

    def __repr__(self):
        return (
            f'<{self.__class__.__name__} protocol={self.protocol!r}, transport={self.transport!r}>'
        )

    @property
    def transport(self):
        if self.protocol is not None:
            return self.protocol.transport

    def set_parser(self, parser):
        self._ctx.set_parser(parser)

    def set_protocol(self, protocol):
        self.protocol = protocol

    def write(self, data):
        self.transport.write(getbytes(data))

    def writelines(self, data):
        self.transport.writelines(getbytes(line) for line in data)

    def can_write_eof(self):
        return self.transport.can_write_eof()

    def write_eof(self):
        self.transport.write_eof()

    def feed_data(self, data):
        self._ctx.feed_data(data)

    def feed_eof(self):
        self._ctx.feed_eof()

    def close(self):
        self.transport.close()

    def is_closing(self):
        return self.transport.is_closing()

    async def wait_until_drained(self):
        await self.protocol.wait_until_drained()

    async def wait_until_closed(self):
        await self.protocol.wait_until_closed()
