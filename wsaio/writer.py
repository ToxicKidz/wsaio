from . import frame as _wsframe


class WebSocketWriter:
    def __init__(self, *, transport, extensions):
        self.transport = transport

        if extensions is not None:
            self.extensions = extensions
        else:
            self.extensions = []

    async def write(self, frame, *, masked=False):
        if not isinstance(frame, _wsframe.WebSocketFrame):
            raise TypeError(f'frame should be a WebSocketFrame, got {frame!r}')

        for extension in self.extensions:
            frame = extension.process(frame)

        self.transport.write(
            frame.opcode
            | (frame.fin << 7)
            | (frame.rsv1 << 6)
            | (frame.rsv2 << 5)
            | (frame.rsv3 << 4)
        )

        mask_bit = masked << 7
        length = len(frame.data)

        if length < 126:
            self.transport.write(mask_bit | length)
        elif length < (1 << 16):
            self.transport.write(mask_bit | 126)
            self.transport.write(length.to_bytes(2, 'big', signed=False))
        else:
            self.transport.write(mask_bit | 127)
            self.transport.write(length.to_bytes(8, 'big', signed=False))

        if masked:
            mask = _wsframe.genmask()
            self.transport.write(mask)
            self.transport.write(_wsframe.mask(frame.data, mask))
        else:
            self.transport.write(frame.data)

    async def ping(self, data, *, masked=False):
        frame = _wsframe.WebSocketFrame(_wsframe.OP_PING, 1, 0, 0, 0, data)
        await self.write(frame, masked=masked)

    async def pong(self, data, *, masked=False):
        frame = _wsframe.WebSocketFrame(_wsframe.OP_PONG, 1, 0, 0, 0, data)
        await self.write(frame, masked=masked)

    async def send(self, data, *, binary=False, masked=False):
        if isinstance(data, str):
            data = data.encode('utf-8')
        elif isinstance(data, memoryview):
            data = data.tobytes()
        elif isinstance(data, bytearray):
            data = bytes(data)
        else:
            raise TypeError(
                f'data shouled be a str or bytes-like object, got {type(data).__name__}'
            )

        op = _wsframe.OP_BINARY if binary else _wsframe.OP_TEXT

        frame = _wsframe.WebSocketFrame(op, 1, 0, 0, 0, data)
        await self.write(frame, masked=masked)
