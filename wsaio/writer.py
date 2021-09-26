from . import frame as _wsframe
from . import util


class WebSocketWriter:
    """A class for writing WebSocket frames to a stream."""

    def __init__(self, *, stream, extensions):
        self.stream = stream

        if extensions is not None:
            self.extensions = extensions
        else:
            self.extensions = []

    async def send_frame(self, frame, *, mask=False):
        """Writes a frame to the stream.

        Arguments:
            frame (WebSocketFrame): The frame to write.

            mask (bool): Whether to mask the frame's data.
        """
        if not isinstance(frame, _wsframe.WebSocketFrame):
            raise TypeError(f'frame should be a WebSocketFrame, got {type(frame).__name__!r}')

        for extension in self.extensions:
            frame = extension.process(frame)

        self.stream.write(
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

        await self.stream.wait_until_drained()

    async def ping(self, data=None, *, mask=False):
        """Writes a ping frame to the stream.

        Arguments:
            data (Optional[str | int | BytesLike]): The data to send in the frame.

            mask (bool): Whether to mask the frame's data.
        """
        frame = _wsframe.WebSocketFrame(op=_wsframe.OP_PING, data=data)
        await self.send_frame(frame, mask=mask)

    async def pong(self, data=None, *, mask=False):
        """Writes a pong frame to the stream.

        Arguments:
            data (Optional[str | int | BytesLike]): The data to send in the frame.

            mask (bool): Whether to mask the frame's data.
        """
        frame = _wsframe.WebSocketFrame(op=_wsframe.OP_PONG, data=data)
        await self.send_frame(frame, mask=mask)

    async def close(self, data=None, *, code=_wsframe.WS_NORMAL_CLOSURE, mask=False):
        """Writes a close frame to the stream.

        Arguments:
            data (Optional[str | int | BytesLike]): The data to send in the frame.

            code (int): The close code.

            mask (bool): Whether to mask the frame's data.
        """
        frame = _wsframe.WebSocketFrame(op=_wsframe.OP_CLOSE, data=data, code=code)
        await self.send_frame(frame, mask=mask)

    async def send(self, data, *, binary=False, mask=False):
        """Writes a data frame to the stream.

        Arguments:
            data (str | int | BytesLike): The data to send in the frame.

            binary (bool): Whether to send the frame with the binary opcode,
                this should be used if the data isn't utf-8.

            mask (bool): Whether to mask the frame's data.
        """
        frame = _wsframe.WebSocketFrame(
            op=_wsframe.OP_BINARY if binary else _wsframe.OP_TEXT, data=data
        )
        await self.send_frame(frame, mask=mask)
