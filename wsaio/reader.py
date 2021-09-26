from . import frame as wsframe
from . import util
from .exceptions import InvalidFrameError

_INVALID_OPCODE_MSG = 'The WebSocket received a frame with an invalid or unknown opcode: {!r}'
_MISSING_CLOSE_CODE_MSG = 'The WebSocket received a close frame with no close code'
_INVALID_CLOSE_CODE_MSG = (
    'The WebSocket received a close frame with an invalid or unknown close code: {!r}'
)
_LARGE_CONTROL_MSG = (
    'The WebSocket received a control frame with a payload length that exceeds 125: {!r}'
)
_FRAGMENTED_CONTROL_MSG = 'The WebSocket received a fragmented control frame'
_INVALID_TEXT_MSG = 'The WebSocket received a text frame with non-UTF-8 data'


class WebSocketReader:
    """A class for reading WebSocket frames from a stream"""

    def __init__(self, *, stream):
        self.stream = stream

    def read_frame(self, ctx):
        fbyte, sbyte = yield from ctx.read(2)

        op = fbyte & 0xF

        fin = (fbyte >> 7) & 1
        masked = (sbyte >> 7) & 1
        length = sbyte & ~(1 << 7)

        if op not in wsframe.WS_OPS:
            raise InvalidFrameError(_INVALID_OPCODE_MSG.format(op), wsframe.WS_PROTOCOL_ERROR)

        if not fin and op > 0x7:
            raise InvalidFrameError(_FRAGMENTED_CONTROL_MSG, wsframe.WS_PROTOCOL_ERROR)

        if length > 125:
            if op > 0x7:
                raise InvalidFrameError(
                    _LARGE_CONTROL_MSG.format(length), wsframe.WS_PROTOCOL_ERROR
                )

            data = yield from ctx.read(2 if length == 126 else 8)
            length = int.from_bytes(data, 'big', signed=False)

        if masked:
            mask = yield from ctx.read(4)

        data = yield from ctx.read(length)

        if masked:
            data = util.mask(data, mask)

        if op == wsframe.OP_CLOSE:
            if len(data) < 2:
                raise InvalidFrameError(_MISSING_CLOSE_CODE_MSG, wsframe.WS_PROTOCOL_ERROR)

            code = int.from_bytes(data[:2], 'big', signed=False)
            if not wsframe.is_close_code(code):
                raise InvalidFrameError(
                    _INVALID_CLOSE_CODE_MSG.format(code), wsframe.WS_PROTOCOL_ERROR
                )

            data = data[2:]
        elif op == wsframe.OP_TEXT:
            try:
                data = data.decode()
            except UnicodeDecodeError:
                raise InvalidFrameError(_INVALID_TEXT_MSG, wsframe.WS_INVALID_PAYLOAD_DATA)

        frame = wsframe.WebSocketFrame(op=op, data=data)
        frame.set_fin(fin)
        frame.set_rsv1((fbyte >> 6) & 1)
        frame.set_rsv2((fbyte >> 5) & 1)
        frame.set_rsv3((fbyte >> 4) & 1)
