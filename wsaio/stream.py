import asyncio

from .exceptions import InvalidDataError
from .util import getbytes


class StreamProtocol(asyncio.Protocol):
    def __init__(self, stream):
        self.loop = stream.loop
        self.transport = None

        self._stream = stream

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
        self._stream._ctx.feed_data(data)

    def eof_received(self):
        self._stream._ctx.feed_eof()
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

        self.reset_parser()
        self._parser = None

        self._error_handler = None

        self._buffer = bytearray()

    def _step_parser(self, arg):
        try:
            self._parser.send(arg)
        except InvalidDataError as exc:
            if self._error_handler is not None:
                self.stream.loop.create_task(self._error_handler(exc))
            else:
                raise

    def _fail_parser(self, error):
        try:
            self._parser.throw(error)
        except Exception as exc:
            if self._error_handler is not None:
                self.loop.create_task(self._error_handler(exc))
            else:
                raise

    def _initialize_parser(self):
        if self._parser is None:
            while True:
                self._parser = self._parsefunc(self)

                try:
                    self._step_parser(None)
                except StopIteration:
                    continue
                else:
                    break

    def set_error_handler(self, func):
        self._error_handler = func

    def set_parser(self, func):
        self._parsefunc = func
        self._parser = None
        self._initialize_parser()

    def reset_parser(self):
        self.set_parser(StreamParserContext.fill)

    def get_buffer(self):
        return self._buffer

    def fill(self):
        data = yield
        self._buffer.extend(data)

    def read(self, amount):
        while len(self._buffer) < amount:
            yield from self.fill()

        data = bytes(self._buffer[:amount])
        del self._buffer[:amount]

        return data

    def feed_data(self, data):
        try:
            self._step_parser(data)
        except StopIteration:
            self._parser = None
            self._initialize_parser()

    def feed_eof(self):
        self._fail_parser(EOFError)


class Stream:
    def __init__(self, *, loop):
        self.loop = loop
        self.protocol = None

        self._ctx = StreamParserContext(self)

    def __repr__(self):
        attrs = [
            ('protocol', self.protocol),
            ('transport', self.transport),
        ]
        inner = ', '.join(f'{name}={value}' for name, value in attrs)
        return f'<{self.__class__.__name__} {inner}>'

    @property
    def transport(self):
        if self.protocol is not None:
            return self.protocol.transport

    async def create_protocol(self, host, port, **kwargs):
        _, self.protocol = await self.loop.create_connection(
            lambda: StreamProtocol(self), host, port, **kwargs
        )
        return self.protocol

    def set_parser(self, parser):
        self._ctx.set_parser(parser)

    def set_error_handler(self, func):
        self._ctx.set_error_handler(func)

    def write(self, data):
        self.transport.write(getbytes(data))

    def writelines(self, data):
        self.transport.writelines(getbytes(line) for line in data)

    def can_write_eof(self):
        return self.transport.can_write_eof()

    def close(self):
        if self.transport is not None:
            self.transport.close()

    def is_closing(self):
        return self.transport.is_closing()

    async def wait_until_drained(self):
        await self.protocol.wait_until_drained()

    async def wait_until_closed(self):
        await self.protocol.wait_until_closed()
