from codecs import getincrementaldecoder
from contextlib import contextmanager
from io import BytesIO, StringIO

from . import frame as wsframe
from . import util
from .exceptions import InvalidFrameError

_INVALID_OPCODE_MSG = 'The WebSocket received a frame with an invalid or unknown opcode: {!r}'
_MISSING_CLOSE_CODE_MSG = 'The WebSocket received a close frame with payload data but no close code'
_INVALID_CLOSE_CODE_MSG = (
    'The WebSocket received a close frame with an invalid or unknown close code: {!r}'
)

_INVALID_LENGTH_MSG = (
    'The WebSocket received a frame with an invalid non-extended payload length: {!r}'
)
_LARGE_CONTROL_MSG = (
    'The WebSocket received a control frame with a payload length that exceeds 125: {!r}'
)

_FRAGMENTED_CONTROL_MSG = 'The WebSocket received a fragmented control frame'
_MEANINGLESS_RSV_BITS_MSG = (
    'The WebSocket received a frame with a reserved bit set but no meaning was negotiated'
)
_NON_UTF_8_MSG = 'The WebSocket received a text or close frame with non-UTF-8 payload data'

_EXPECTED_CONT_MSG = (
    'The WebSocket received a non-continuation data frame while reading a fragmented frame'
)
_UNEXPECTED_CONT_MSG = (
    'The WebSocket received a continuation frame but no fragmented frame was received'
)

_IncrementalDecoder = getincrementaldecoder('utf-8')


class WebSocketReader:
    """A class for reading WebSocket frames from a stream."""

    def __init__(self, *, stream):
        self.stream = stream

        self._fragment_buffer = None
        self._fragment_decoder = None
        self._fragmented_frame = None

        self._on_ping = None
        self._on_pong = None
        self._on_text = None
        self._on_binary = None
        self._on_close = None

    def __repr__(self):
        return f'<{self.__class__.__name__} stream={self.stream!r}>'

    @contextmanager
    def _suppress_decode_error(self):
        try:
            yield
        except UnicodeDecodeError:
            raise InvalidFrameError(_NON_UTF_8_MSG, wsframe.WS_INVALID_PAYLOAD_DATA)

    def _run_callback(self, frame):
        if frame.is_ping():
            coro = self._on_ping(frame.data)
        elif frame.is_pong():
            coro = self._on_pong(frame.data)
        elif frame.is_text():
            coro = self._on_text(frame.data)
        elif frame.is_binary():
            coro = self._on_binary(frame.data)
        elif frame.is_close():
            coro = self._on_close(frame.code, frame.data)

        self.stream.loop.create_task(coro)

    def _setup_fragmenter(self, frame, data):
        self._fragmented_frame = frame
        if frame.is_text():
            self._fragment_decoder = _IncrementalDecoder()
            self._fragment_buffer = StringIO()
        else:
            self._fragment_buffer = BytesIO()

        self._write_fragment(data)

    def _write_fragment(self, data):
        if self._fragment_decoder is not None:
            data = self._fragment_decoder.decode(data)
        self._fragment_buffer.write(data)

    def _reset_fragmenter(self):
        self._fragmented_frame = None
        self._fragment_buffer = None
        self._fragment_decoder = None

    def read_frame(self, ctx):
        fbyte, sbyte = yield from ctx.read(2)

        masked = (sbyte >> 7) & 1
        length = sbyte & ~(1 << 7)

        frame = wsframe.WebSocketFrame.from_head(fbyte)

        if frame.op not in wsframe.WS_OPS:
            raise InvalidFrameError(_INVALID_OPCODE_MSG.format(frame.op), wsframe.WS_PROTOCOL_ERROR)

        if any((frame.rsv1, frame.rsv2, frame.rsv3)):
            raise InvalidFrameError(_MEANINGLESS_RSV_BITS_MSG, wsframe.WS_PROTOCOL_ERROR)

        if frame.is_control():
            yield from self._handle_control_frame(ctx, frame, masked, length)
        else:
            yield from self._handle_data_frame(ctx, frame, masked, length)

    def _read_length(self, ctx, length):
        if length == 126:
            data = yield from ctx.read(2)
        elif length == 127:
            data = yield from ctx.read(8)
        else:
            if length > 127:  # XXX: Is this even possible?
                raise InvalidFrameError(_INVALID_LENGTH_MSG, wsframe.WS_PROTOCOL_ERROR)

            return length

        return int.from_bytes(data, 'big', signed=False)

    def _read_payload(self, ctx, length, masked):
        if masked:
            mask = yield from ctx.read(4)
            data = yield from ctx.read(length)
            return util.mask(data, mask)
        else:
            data = yield from ctx.read(length)
            return data

    def _set_close_code(self, frame, data):
        if not data:
            return b''
        elif len(data) < 2:
            raise InvalidFrameError(_MISSING_CLOSE_CODE_MSG, wsframe.WS_PROTOCOL_ERROR)

        code = int.from_bytes(data[:2], 'big', signed=False)

        if not wsframe.is_close_code(code):
            raise InvalidFrameError(_INVALID_CLOSE_CODE_MSG.format(code), wsframe.WS_PROTOCOL_ERROR)

        frame.set_code(code)

        return data[2:]

    def _handle_control_frame(self, ctx, frame, masked, length):
        if not frame.fin:
            raise InvalidFrameError(_FRAGMENTED_CONTROL_MSG, wsframe.WS_PROTOCOL_ERROR)

        if length > 125:
            raise InvalidFrameError(_LARGE_CONTROL_MSG.format(length), wsframe.WS_PROTOCOL_ERROR)

        data = yield from self._read_payload(ctx, length, masked)

        if frame.is_close():
            data = self._set_close_code(frame, data)

            with self._suppress_decode_error():
                frame.set_data(data.decode('utf-8'))
        else:
            frame.set_data(data)

        self._run_callback(frame)

    def _handle_data_frame(self, ctx, frame, masked, length):
        length = yield from self._read_length(ctx, length)
        data = yield from self._read_payload(ctx, length, masked)

        if frame.is_continuation():
            if self._fragmented_frame is None:
                raise InvalidFrameError(_UNEXPECTED_CONT_MSG, wsframe.WS_PROTOCOL_ERROR)

            with self._suppress_decode_error():
                self._write_fragment(data)
        elif self._fragmented_frame is not None:
            raise InvalidFrameError(_EXPECTED_CONT_MSG, wsframe.WS_PROTOCOL_ERROR)

        if not frame.fin:
            if self._fragmented_frame is None:
                with self._suppress_decode_error():
                    self._setup_fragmenter(frame, data)
        else:
            if self._fragmented_frame is not None:
                frame = self._fragmented_frame
                data = self._fragment_buffer.getvalue()
                self._reset_fragmenter()
            elif frame.is_text():
                with self._suppress_decode_error():
                    data = data.decode('utf-8')

            frame.set_data(data)

            self._run_callback(frame)
