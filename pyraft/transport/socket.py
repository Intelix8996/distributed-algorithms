import asyncio

from pyraft.transport.base import MessageTransport


class SocketMessageTransport(MessageTransport):

    async def send_message(self, host: str, port: int, msg: str) -> str:
        reader, writer = await asyncio.open_connection(host, port)

        print(f"Send: {msg!r}")
        writer.write(msg.encode())
        await writer.drain()

        data = await reader.read(100)
        data = data.decode()
        print(f"Received response: {data!r}")

        # print('Close the connection')
        writer.close()

        return data

    async def handle_message(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        data = await reader.read(100)
        message = data.decode()
        addr = writer.get_extra_info("peername")

        print(f"Received {message!r} from {addr!r}")

        if self._message_callback:
            response = await self._message_callback(message)
        else:
            response = ""

        print(f"Send response: {response!r}")
        writer.write(response.encode())
        await writer.drain()

        # print("Close the connection")
        writer.close()

    async def start_server(self, host: str, port: int) -> None:
        server = await asyncio.start_server(self.handle_message, host, port)

        addr = server.sockets[0].getsockname()
        print(f"Serving on {addr}")

        async with server:
            await server.serve_forever()
