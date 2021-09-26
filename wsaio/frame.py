from .util import getbytes

OP_CONTINUATION = 0x0
OP_TEXT = 0x1
OP_BINARY = 0x2
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA

WS_OPS = (
    OP_CONTINUATION,
    OP_TEXT,
    OP_BINARY,
    OP_CLOSE,
    OP_PING,
    OP_PONG,
)

WS_NORMAL_CLOSURE = 1000
WS_GOING_AWAY = 1001
WS_PROTOCOL_ERROR = 1002
WS_UNSUPPORTED_DATA = 1003
WS_NO_STATUS_RECEIVED = 1005
WS_ABNORMAL_CLOSURE = 1006
WS_INVALID_PAYLOAD_DATA = 1007
WS_POLICY_VIOLATION = 1008
WS_MESSAGE_TOO_BIG = 1009
WS_MANDATORY_EXTENSION = 1010
WS_INTERNAL_SERVER_ERROR = 1011
WS_TLS_HANDSHAKE = 1015

WS_CLOSE_CODES = (
    WS_NORMAL_CLOSURE,
    WS_GOING_AWAY,
    WS_PROTOCOL_ERROR,
    WS_UNSUPPORTED_DATA,
    WS_NO_STATUS_RECEIVED,
    WS_ABNORMAL_CLOSURE,
    WS_INVALID_PAYLOAD_DATA,
    WS_POLICY_VIOLATION,
    WS_MESSAGE_TOO_BIG,
    WS_MANDATORY_EXTENSION,
    WS_INTERNAL_SERVER_ERROR,
    WS_TLS_HANDSHAKE
)


class WebSocketFrame:
    __slots__ = ('op', 'fin', 'rsv1', 'rsv2', 'rsv3', 'data')

    def __init__(self, *, op, data, code=None):
        self.op = op
        self.data = getbytes(data)
        self.code = code

        self.set_fin(True)
        self.set_rsv1(False)
        self.set_rsv2(False)
        self.set_rsv3(False)

    def set_fin(self, value):
        self.fin = bool(value)

    def set_rsv1(self, value):
        self.rsv1 = bool(value)

    def set_rsv2(self, value):
        self.rsv2 = bool(value)

    def set_rsv3(self, value):
        self.rsv2 = bool(value)

    def validate(self):
        if self.op not in WS_OPS:
            raise ValueError(f'Invalid opcode: {self.op!r}')

        if self.op > 0x7:
            length = len(self.data)
            if self.code is not None:
                length += 2

            if len(self.data) > 125:
                raise ValueError(f'Control frame data length exceeds 125: {length}')

            if not self.fin:
                raise ValueError('Control frame shouldn\'t be fragmented')

        if self.code is not None:
            if self.op != OP_CLOSE:
                raise ValueError(f'Invalid opcode for frame with close code: {self.code}')

            if self.code <= 2999 and self.code not in WS_CLOSE_CODES:
                raise ValueError(f'Invalid close code: {self.code}')
