from enum import StrEnum


class NodeState(StrEnum):
    LEADER = "leader"
    CANDIDATE = "candidate"
    FOLLOWER = "follower"
