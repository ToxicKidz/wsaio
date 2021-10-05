import asyncio

from wsaio.client import WebSocketClient


class TestClient(WebSocketClient):
    async def on_text(self, data):
        await self.write(data)

    async def on_binary(self, data):
        await self.write(data, binary=True)


async def main(loop):
    try:
        for i in range(1, 302):
            print(f'Running test case {i}')
            client = TestClient(loop=loop)
            await client.connect(f'ws://localhost:9001/runCase?case={i}&agent=wsaio')

            try:
                await asyncio.wait_for(client.stream.wait_until_closed(), timeout=10)
            except asyncio.TimeoutError:
                print(f'Test case {i} timed out')
                client.stream.close()
                break
    finally:
        client = TestClient(loop=loop)
        await client.connect('ws://localhost:9001/updateReports?agent=wsaio')


loop = asyncio.get_event_loop()
loop.run_until_complete(main(loop))
