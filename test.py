import asyncio

from wsaio.stream import Stream, StreamProtocol


def parser(ctx):
    while True:
        data = yield from ctx.read(40)
        print(data)


async def main(loop):
    stream = Stream(loop)
    stream.set_parser(parser)
    await loop.create_connection(lambda: StreamProtocol(stream), 'google.com', 443, ssl=True)
    stream.write('SDJDJDJDJD\r\n\r\n')


loop = asyncio.get_event_loop()
loop.create_task(main(loop))
loop.run_forever()
