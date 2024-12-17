import asyncio
from pathlib import Path

from pyraft.server.arguments import parse_args
from pyraft.node import Node
from pyraft.node.config import read_node_config
from pyraft.node.state import NodeState
from pyraft.transport.socket import SocketMessageTransport

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "nodes.toml"


def main():
    args = parse_args()

    node_config = read_node_config(CONFIG_PATH)

    node_initial_state = args.state if args.state is not None else NodeState.FOLLOWER

    node = Node(args.name, node_config, SocketMessageTransport(), node_initial_state)

    asyncio.run(node.start())


if __name__ == "__main__":
    main()
