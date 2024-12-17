from enum import StrEnum

from pydantic import BaseModel

from pyraft.commands.types import DeleteCommand, SetCommand, StateMachineCommand


class MessageType(StrEnum):
    APPEND_ENTRIES = "append_entries"
    REQUEST_VOTE = "request_vote"
    CLIENT_MESSAGE = "client_message"


class BaseMessage(BaseModel):
    msg_type: MessageType
    """Type of a message"""


class RaftMessage(BaseMessage):
    sender_term: int
    """Senders's term"""

    sender_id: str
    """Sender identifier"""

    prev_log_index: int
    prev_log_term: int


class RequestVoteMessage(RaftMessage):
    msg_type: MessageType = MessageType.REQUEST_VOTE


class AppendEntriesMessage(RaftMessage):
    msg_type: MessageType = MessageType.APPEND_ENTRIES

    entries: list[tuple[int, SetCommand | DeleteCommand]]
    """Entries to append (Empty for heartbeat)"""

    leader_commit: int
    """Leader's commit index"""


class ClientMessage(BaseMessage):
    msg_type: MessageType = MessageType.CLIENT_MESSAGE

    text: str
    """Textual message from client"""


class BaseResponse(BaseModel): ...


class RequestVoteResponse(BaseResponse):
    term: int
    """Current term (for candidate to update itself)"""

    vote_granted: bool
    """Vote result"""


class AppendEntriesResponse(BaseResponse):
    term: int
    """Current term (for leader to update itself)"""

    success: bool
    """ Whether follower contained entry matching"""


class ClientResponse(BaseResponse):
    text: str
    """Textual response for client"""


class TimeoutResponse(BaseResponse): ...
