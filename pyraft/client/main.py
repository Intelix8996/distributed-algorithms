import asyncio
from collections.abc import Awaitable, Callable
import json
from pathlib import Path
from types import SimpleNamespace
from pyraft.client.arguments import parse_args
from pyraft.node.config import read_node_config
from pyraft.node.messages import ClientMessage, MessageType
from pyraft.transport.socket import SocketMessageTransport

SEND_TIMEOUT = .1


async def repl(send_message: Callable[[str], Awaitable[str]]):
    while True:
        cmd = await asyncio.to_thread(input)
        msg = ClientMessage(text=cmd)

        try:
            async with asyncio.timeout(SEND_TIMEOUT):
                response = await send_message(msg.model_dump_json())
        except TimeoutError:
            print("Connection timeout")
        else:
            obj = json.loads(response, object_hook=lambda d: SimpleNamespace(**d))

            print(obj.text)


def main():
    args = parse_args()
    node_config = read_node_config(Path("./config/nodes.toml"))
    node_info = node_config.get_node_info(args.name)
    transport = SocketMessageTransport()

    async def send_message(msg: str) -> str:
        return await transport.send_message(node_info.address, node_info.port, msg)

    asyncio.run(repl(send_message))


if __name__ == "__main__":
    main()
