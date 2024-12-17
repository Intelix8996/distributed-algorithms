import tomllib

from dataclasses import dataclass
from os import PathLike


@dataclass
class NodeInfo:
    address: str
    port: int

    def as_tuple(self) -> tuple[str, int]:
        return self.address, self.port


@dataclass
class NodeConifg:
    nodes: dict[str, NodeInfo]

    def get_node_info(self, name: str) -> NodeInfo:
        return self.nodes[name]
    
    def get_other_nodes(self, name: str) -> list[NodeInfo]:
        return [ node_info for node_name, node_info in self.nodes.items() if node_name != name ]
    
    def get_node_count(self) -> int:
        return len(self.nodes)


CONFIG_ADDRESS_ENTRY = "addr"
CONFIG_PORT_ENTRY = "port"


def read_node_config(path: PathLike[str]) -> NodeConifg:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    nodes: dict[str, NodeInfo] = {}

    for name, info in data.items():
        nodes[name] = NodeInfo(info[CONFIG_ADDRESS_ENTRY], info[CONFIG_PORT_ENTRY])

    return NodeConifg(nodes)
