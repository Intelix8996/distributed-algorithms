from typing import Protocol

from pyraft.node.messages import AppendEntriesMessage, AppendEntriesResponse, RequestVoteMessage, RequestVoteResponse


class EventHandler(Protocol):
    
    # Node timeouts
    async def heartbeat_timeout_elapsed(self) -> None: ...
    async def election_timeout_elapsed(self) -> None: ...

    # Local IO
    async def handle_terminal(self, string: str) -> None: ...

    # Messages
    async def handle_append_entries(self, msg: AppendEntriesMessage) -> AppendEntriesResponse: ...
    async def handle_request_vote(self, msg: RequestVoteMessage) -> RequestVoteResponse: ...
