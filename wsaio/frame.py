from .util import tobytes

OP_CONTINUATION = 0x0
OP_TEXT = 0x1
OP_BINARY = 0x2
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA

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


class WebSocketFrame:
    __slots__ = ('op', 'fin', 'rsv1', 'rsv2', 'rsv3', 'data')

    def __init__(self, *, op, data, code=None):
        self.op = op
        self.data = tobytes(data)

        self.set_fin(True)
        self.set_rsv1(False)
        self.set_rsv2(False)
        self.set_rsv3(False)

        if code is not None:
            self.data = code.to_bytes(2, 'big', signed=False) + self.data

        if self.is_control():
            if len(self.data) > 125:
                raise ValueError('Control frame data length shouldn\'t be greater than 125')

    def is_control(self):
        return self.op in (OP_CONTINUATION, OP_CLOSE, OP_PING, OP_PONG)

    def set_fin(self, value):
        self.fin = bool(value)

    def set_rsv1(self, value):
        self.rsv1 = bool(value)

    def set_rsv2(self, value):
        self.rsv2 = bool(value)

    def set_rsv3(self, value):
        self.rsv2 = bool(value)
