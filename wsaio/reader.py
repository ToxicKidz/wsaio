from . import frame as wsframe
from . import util
from .exceptions import InvalidFrameError

_INVALID_OPCODE_MSG = 'The WebSocket received a frame with an invalid or unknown opcode: {!r}'
_MISSING_CLOSE_CODE_MSG = 'The WebSocket received a close frame with no close code'
_INVALID_CLOSE_CODE_MSG = (
    'The WebSocket received a close frame with an invalid or unknown close code: {!r}'
)
_INVALID_LENGTH_MSG = 'The WebSocket received a frame with an invalid length: {!r}'
_LARGE_CONTROL_MSG = (
    'The WebSocket received a control frame with a payload length that exceeds 125: {!r}'
)
_FRAGMENTED_CONTROL_MSG = 'The WebSocket received a fragmented control frame'
_NON_UTF_8_MSG = 'The WebSocket received a text or control frame with non-UTF-8 payload data'


class WebSocketReader:
    """A class for reading WebSocket frames from a stream."""

    def __init__(self, *, stream):
        self.stream = stream

        self._callback = None

    def set_callback(self, callback):
        self._callback = callback

    def run_callback(self, frame):
        if self._callback is not None:
            return self._callback(frame)

    def read_frame(self, ctx):
        fbyte, sbyte = yield from ctx.read(2)

        masked = (sbyte >> 7) & 1
        length = sbyte & ~(1 << 7)

        frame = wsframe.WebSocketFrame.from_head(fbyte)

        if frame.op not in wsframe.WS_OPS:
            raise InvalidFrameError(_INVALID_OPCODE_MSG.format(frame.op), wsframe.WS_PROTOCOL_ERROR)

        if frame.is_control():
            yield from self._handle_control_frame(ctx, frame, masked, length)
        else:
            yield from self._handle_data_frame(ctx, frame, masked, length)

        self.run_callback(frame)

    def _read_length(self, ctx, length):
        if length == 126:
            data = yield from ctx.read(2)
        elif length == 127:
            data = yield from ctx.read(8)
        else:
            if length > 127:  # XXX: Is this even possible?
                raise InvalidFrameError(_INVALID_LENGTH_MSG, wsframe.WS_PROTOCOL_ERROR)

            data = yield from ctx.read(length)

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
        if len(data) < 2:
            raise InvalidFrameError(_MISSING_CLOSE_CODE_MSG, wsframe.WS_PROTOCOL_ERROR)

        code = int.from_bytes(data[:2], 'big', signed=False)

        if not wsframe.is_close_code(code):
            raise InvalidFrameError(_INVALID_CLOSE_CODE_MSG, wsframe.WS_PROTOCOL_ERROR)

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

        try:
            frame.set_data(data.decode())
        except UnicodeDecodeError:
            raise InvalidFrameError(_NON_UTF_8_MSG, wsframe.WS_INVALID_PAYLOAD_DATA)

    def _handle_data_frame(self, ctx, frame, masked, length):
        length = yield from self._read_length(ctx, length)
        data = yield from self._read_payload(ctx, length, masked)

        if frame.is_text():
            try:
                frame.set_data(data.decode())
            except UnicodeDecodeError:
                raise InvalidFrameError(_NON_UTF_8_MSG, wsframe.WS_INVALID_PAYLOAD_DATA)
        else:
            frame.set_data(data)
