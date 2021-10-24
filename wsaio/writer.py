from . import frame as wsframe
from . import util


class WebSocketWriter:
    """A class for writing WebSocket frames to a stream."""

    def __init__(self, *, stream):
        self.stream = stream

    async def write_frame(self, frame, *, mask=False):
        """Writes a frame to the stream.

        Arguments:
            frame (WebSocketFrame): The frame to write.

            mask (bool): Whether to send the frame with a mask.
        """
        if not isinstance(frame, wsframe.WebSocketFrame):
            raise TypeError(f'frame should be a WebSocketFrame, got {type(frame).__name__!r}')

        frame.validate()

        data = frame.data
        if isinstance(data, str):
            data = data.encode('utf-8')

        length = len(data)

        buffer = bytearray(2)
        buffer[0] = frame.head

        masked = mask << 7

        if length < 126:
            buffer[1] = masked | length
        elif length < (1 << 16):
            buffer[1] = masked | 126
            buffer.extend(length.to_bytes(2, 'big', signed=False))
        else:
            buffer[1] = masked | 127
            buffer.extend(length.to_bytes(8, 'big', signed=False))

        if frame.code is not None:
            data = frame.code.to_bytes(2, 'big', signed=False) + data

        if mask:
            mask = util.genmask()
            buffer.extend(mask)
            buffer.extend(util.mask(data, mask))
        else:
            buffer.extend(data)

        self.stream.write(buffer)

        await self.stream.wait_until_drained()

    async def ping(self, data=None, *, mask=False):
        """Writes a ping frame to the stream.

        Arguments:
            data (Optional[str | int | BytesLike]): The data to send in the frame.

            mask (bool): Whether to send the frame with a mask.
        """
        frame = wsframe.WebSocketFrame(op=wsframe.OP_PING, data=data)
        await self.write_frame(frame, mask=mask)

    async def pong(self, data=None, *, mask=False):
        """Writes a pong frame to the stream.

        Arguments:
            data (Optional[str | int | BytesLike]): The data to send in the frame.

            mask (bool): Whether to send the frame with a mask.
        """
        frame = wsframe.WebSocketFrame(op=wsframe.OP_PONG, data=data)
        await self.write_frame(frame, mask=mask)

    async def close(self, data=None, *, code=wsframe.WS_NORMAL_CLOSURE, mask=False):
        """Writes a close frame to the stream.

        Arguments:
            data (Optional[str | int | BytesLike]): The data to send in the frame.

            code (int): The close code.

            mask (bool): Whether to send the frame with a mask.
        """
        frame = wsframe.WebSocketFrame(op=wsframe.OP_CLOSE, data=data, code=code)
        await self.write_frame(frame, mask=mask)

        self.stream.close()

    async def write(self, data, *, binary=False, mask=False):
        """Writes a data frame to the stream.

        Arguments:
            data (str | int | BytesLike): The data to send in the frame.

            binary (bool): Whether to send the frame with the binary opcode,
                this should be used if the data isn't utf-8.

            mask (bool): Whether to send the frame with a mask.
        """
        frame = wsframe.WebSocketFrame(
            op=wsframe.OP_BINARY if binary else wsframe.OP_TEXT, data=data
        )
        await self.write_frame(frame, mask=mask)
