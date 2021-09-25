import os
from collections import namedtuple

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

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


WebSocketFrame = namedtuple('WebSocketFrame', ('opcode', 'fin', 'rsv1', 'rsv2', 'rsv3', 'data'))


def genmask():
    return os.urandom(4)


def mask(data, mask):
    return bytes(data[i] ^ mask[i % 4] for i in range(len(data)))
