<h1 align="center">wsaio</h1>
<p align="center">
<a href="https://pypi.org/project/wsaio"><img height="20" alt="PyPI version" src="https://img.shields.io/pypi/v/wsaio"></a>
<a href="https://pypi.org/project/wsaio"><img height="20" alt="Supported python versions" src="https://img.shields.io/pypi/pyversions/wsaio"></a>
</p>
wsaio is a callback-based WebSocket library for Python.

# Examples
```py
import asyncio

from wsaio import WebSocketClient


class EchoClient(WebSocketClient):
    async def on_text(self, data):
        await self.write(data)

    async def on_binary(self, data):
        await self.write(data, binary=True)


async def main(loop):
    client = EchoClient(loop=loop)

    await client.connect('wss://localhost/helloWorld')
    await client.wait_until_closed()


loop = asyncio.get_event_loop()
loop.run_until_complete(main(loop))
```
