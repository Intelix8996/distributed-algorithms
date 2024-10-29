from dataclasses import dataclass
from enum import StrEnum


class MessageType(StrEnum):
    APPEND_ENTRIES = "append_entries"
    REQUEST_VOTE = "request_vote"


@dataclass
class BaseMessage:
    msg_type: MessageType
    sender: str
    sender_term: int


@dataclass
class RequestVoteMessage(BaseMessage):
    msg_type = MessageType.REQUEST_VOTE


@dataclass
class AppendEntriesMessage(BaseMessage):
    msg_type = MessageType.APPEND_ENTRIES

    entries: list


@dataclass
class BaseResponse: ...


@dataclass
class RequestVoteResponse(BaseResponse):
    vote: bool


@dataclass
class AppendEntriesResponse(BaseResponse): ...


@dataclass
class TimeoutResponse(BaseResponse): ...
