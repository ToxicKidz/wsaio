from .util import getbytes

OP_CONTINUATION = 0x0
OP_TEXT = 0x1
OP_BINARY = 0x2
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA

WS_OPS = {
    OP_CONTINUATION: 'Continuation',
    OP_TEXT: 'Text',
    OP_BINARY: 'Binary',
    OP_CLOSE: 'Close',
    OP_PING: 'Ping',
    OP_PONG: 'Pong',
}

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

WS_CLOSE_CODES = {
    WS_NORMAL_CLOSURE: 'Normal Closure',
    WS_GOING_AWAY: 'Going Away',
    WS_PROTOCOL_ERROR: 'Protocol Error',
    WS_UNSUPPORTED_DATA: 'Unsupported Data',
    WS_NO_STATUS_RECEIVED: 'No Status Received',
    WS_ABNORMAL_CLOSURE: 'Abnormal Closure',
    WS_INVALID_PAYLOAD_DATA: 'Invalid Payload Data',
    WS_POLICY_VIOLATION: 'Policy Violation',
    WS_MESSAGE_TOO_BIG: 'Message Too Big',
    WS_MANDATORY_EXTENSION: 'Mandatory Extension',
    WS_INTERNAL_SERVER_ERROR: 'Internal Server Error',
    WS_TLS_HANDSHAKE: 'TLS Handshake'
}


def is_close_code(code):
    return code in WS_CLOSE_CODES or 3000 <= code <= 4999


class WebSocketFrame:
    __slots__ = ('head', 'data', 'code')

    def __init__(self, *, op, data=None, code=None):
        self.head = 0
        self.set_op(op)
        self.set_data(data)
        self.set_code(code)
        self.set_fin(True)

    @classmethod
    def from_head(cls, head, *, data=None, code=None):
        self = cls.__new__(cls)

        self.head = head
        self.set_data(data)
        self.set_code(code)

        return self

    def __repr__(self):
        name = WS_OPS.get(self.op, '<unknown>')
        return f'<{name} frame at {hex(id(self))}>'

    def is_control(self):
        return self.op > 0x7

    def is_continuation(self):
        return self.op == OP_CONTINUATION

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
        if isinstance(data, str):
            self.data = data
        else:
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

        if self.is_control():
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
