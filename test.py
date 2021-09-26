import asyncio

from wsaio.protocol import Stream, StreamProtocol


async def parser(stream):
    while True:
        print(await stream.read(40))


async def main(loop):
    stream = Stream(loop, lambda: parser(stream))
    await loop.create_connection(lambda: StreamProtocol(stream), 'google.com', 443, ssl=True)

    stream.write('SDJDJDJDJD\r\n\r\n')


loop = asyncio.get_event_loop()
loop.create_task(main(loop))
loop.run_forever()
