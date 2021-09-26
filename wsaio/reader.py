from . import frame as wsframe
from . import util


class WebSocketReader:
    """A class for reading WebSocket frames from a stream"""

    def __init__(self, *, stream):
        self.stream = stream

    def read_frame(self, ctx):
        fbyte, sbyte = yield from ctx.read(2)

        masked = (sbyte >> 7) & 1
        length = sbyte & ~(1 << 7)

        if length > 125:
            data = yield from ctx.read(2 if length == 126 else 8)
            length = int.from_bytes(data, 'big', signed=False)

        if masked:
            mask = yield from ctx.read(4)

        data = yield from ctx.read(length)

        if masked:
            data = util.mask(data, mask)

        frame = wsframe.WebSocketFrame(op=fbyte & 0xF, data=data)
        frame.set_fin((fbyte >> 7) & 1)
        frame.set_rsv1((fbyte >> 6) & 1)
        frame.set_rsv2((fbyte >> 5) & 1)
        frame.set_rsv3((fbyte >> 4) & 1)
