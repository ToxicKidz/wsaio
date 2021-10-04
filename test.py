import asyncio

from wsaio.client import WebSocketClient


class MyClient(WebSocketClient):
    async def on_text(self, data):
        await self.write(data)

    async def on_binary(self, data):
        await self.write(data, binary=True)


async def main(loop):
    for i in range(1, 50):
        print(f'Running test case {i}')
        client = MyClient(loop=loop)
        await client.connect(f'ws://localhost:9001/runCase?case={i}&agent=wsaio')

        try:
            await asyncio.wait_for(client.stream.wait_until_closed(), timeout=5)
        except asyncio.TimeoutError:
            print(f'Test case {i} timed out')
            client.stream.close()
            break

    client = MyClient(loop=loop)
    await client.connect('ws://localhost:9001/updateReports?agent=wsaio')


loop = asyncio.get_event_loop()
loop.run_until_complete(main(loop))
