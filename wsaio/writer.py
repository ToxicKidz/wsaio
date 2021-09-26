from . import frame as _wsframe
from . import util


class WebSocketWriter:
    def __init__(self, *, protocol, extensions):
        self.protocol = protocol

        if extensions is not None:
            self.extensions = extensions
        else:
            self.extensions = []

    async def send_frame(self, frame, *, mask=False):
        if not isinstance(frame, _wsframe.WebSocketFrame):
            raise TypeError(f'frame should be a WebSocketFrame, got {type(frame).__name__!r}')

        for extension in self.extensions:
            frame = extension.process(frame)

        self.protocol.write(
            frame.op
            | (frame.fin << 7)
            | (frame.rsv1 << 6)
            | (frame.rsv2 << 5)
            | (frame.rsv3 << 4)
        )

        mask_bit = mask << 7
        length = len(frame.data)

        if length < 126:
            self.stream.write(mask_bit | length)
        elif length < (1 << 16):
            self.stream.write(mask_bit | 126)
            self.stream.write(length.to_bytes(2, 'big', signed=False))
        else:
            self.stream.write(mask_bit | 127)
            self.stream.write(length.to_bytes(8, 'big', signed=False))

        if mask:
            mask = util.genmask()
            self.stream.write(mask)
            self.stream.write(util.mask(frame.data, mask))
        else:
            self.stream.write(frame.data)

    async def ping(self, data=None, *, mask=False):
        frame = _wsframe.WebSocketFrame(op=_wsframe.OP_PING, data=data)
        await self.send_frame(frame, mask=mask)

    async def pong(self, data=None, *, mask=False):
        frame = _wsframe.WebSocketFrame(op=_wsframe.OP_PONG, data=data)
        await self.send_frame(frame, mask=mask)

    async def close(self, data=None, *, code=_wsframe.WS_NORMAL_CLOSURE, mask=False):
        frame = _wsframe.WebSocketFrame(op=_wsframe.OP_CLOSE, data=data, code=code)
        await self.send_frame(frame, mask=mask)

    async def send(self, data, *, binary=False, mask=False):
        frame = _wsframe.WebSocketFrame(
            op=_wsframe.OP_BINARY if binary else _wsframe.OP_TEXT, data=data
        )
        await self.send_frame(frame, mask=mask)
