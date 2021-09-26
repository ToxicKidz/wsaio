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


def is_close_code(code):
    return code in WS_CLOSE_CODES or 3000 <= code <= 4999


class WebSocketFrame:
    __slots__ = ('head', 'data', 'code')

    def __init__(self, *, op, data=None, code=None, fin=True, rsv1=False, rsv2=False, rsv3=False):
        self.head = 0

        self.set_op(op)
        self.set_data(data)
        self.set_code(code)
        self.set_fin(fin)
        self.set_rsv1(rsv1)
        self.set_rsv2(rsv2)
        self.set_rsv3(rsv3)

    def __repr__(self):
        if self.is_text():
            name = 'Text'
        elif self.is_binary():
            name = 'Binary'
        elif self.is_ping():
            name = 'Ping'
        elif self.is_pong():
            name = 'Pong'
        elif self.is_close():
            name = 'Close'

        return f'<{name} frame at {hex(id(self))}>'

    def is_control(self):
        return self.op > 0x7

    def is_text(self):
        return self.op == OP_TEXT

    def is_binary(self):
        return self.op == OP_BINARY

    def is_ping(self):
        return self.op == OP_PING

    def is_pong(self):
        return self.op == OP_PONG

    def is_close(self):
        return self.op == OP_CLOSE

    @property
    def op(self):
        return self.head & 0xF

    @property
    def fin(self):
        return (self.head >> 7) & 1

    @property
    def rsv1(self):
        return (self.head >> 6) & 1

    @property
    def rsv2(self):
        return (self.head >> 5) & 1

    @property
    def rsv3(self):
        return (self.head >> 4) & 1

    def set_op(self, op):
        self.head |= int(op)

    def set_data(self, data):
        self.data = getbytes(data)

    def set_fin(self, value):
        self.head |= int(value) << 7

    def set_rsv1(self, value):
        self.head |= int(value) << 6

    def set_rsv2(self, value):
        self.head |= int(value) << 5

    def set_rsv3(self, value):
        self.head |= int(value) << 4

    def set_code(self, code):
        if code is not None:
            self.code = int(code)
        else:
            self.code = None

    def validate(self):
        if self.op not in WS_OPS:
            raise ValueError('Invalid opcode')

        if self.op > 0x7:
            length = len(self.data)
            if self.code is not None:
                length += 2

            if len(self.data) > 125:
                raise ValueError('Control frame data length shouldn\'t exceed 125')

            if not self.fin:
                raise ValueError('Control frame shouldn\'t be fragmented')

        if self.code is not None:
            if self.op != OP_CLOSE:
                raise ValueError('Non-close frame should not have a close code')

            if not is_close_code(self.code):
                raise ValueError('Invalid close code')
