import asyncio
import random
from typing import overload
from pyraft.commands.parser import parse_command
from pyraft.commands.types import (
    BaseCommand,
    DeleteCommand,
    QueryCommand,
    SetCommand,
    StateMachineCommand,
)
from pyraft.event import EventManager
from pyraft.node.log import NodeLog
from pyraft.node.messages import (
    AppendEntriesMessage,
    AppendEntriesResponse,
    ClientMessage,
    ClientResponse,
    MessageType,
    RaftMessage,
    RequestVoteMessage,
    RequestVoteResponse,
    TimeoutResponse,
)
from pyraft.node.config import NodeConifg, NodeInfo
from pyraft.node.state import NodeState
from pyraft.storage.kv import DictStorage, KeyValueStorage
from pyraft.transport.socket import MessageTransport

ELECTION_TIMEOUT = 5
ELECTION_TIMEOUT_RANGE = 3


class Node:

    # Synchronization objects
    _append_entries_event: asyncio.Event

    # State machine
    _storage: KeyValueStorage[str, str]

    # Persistent state
    _current_term: int
    """Latest term server has seen"""

    _voted_for: str | None
    """Candidate that received vote in current term"""

    _log: NodeLog
    """Log entries"""

    # Volatile state
    _commit_index: int
    """Index of highest log entry known to be committed"""

    _last_applied: int
    """Index of highest log entry applied to state machine"""

    # Volatile state for leaders
    _next_index: dict[str, int]
    """For each server, index of the next log entry to send to that server"""

    _match_index: dict[str, int]
    """For each server, index of highest log entry known to be replicated on server"""

    def __init__(
        self,
        name: str,
        node_config: NodeConifg,
        transport: MessageTransport,
        initial_state: NodeState = NodeState.FOLLOWER,
        term: int = 0,
        voted_for: str | None = None,
    ) -> None:
        self._name = name
        self._node_config = node_config

        election_timeout = ELECTION_TIMEOUT + random.randint(
            -ELECTION_TIMEOUT_RANGE, ELECTION_TIMEOUT_RANGE
        )

        print("Election timeout:", election_timeout)

        self._event_handler = EventManager(transport, election_timeout=election_timeout)
        self._event_handler.register_event_handler(self)

        self._storage = DictStorage()

        self._state = initial_state

        # Persistent state
        self._current_term = term
        self._voted_for = voted_for
        self._log = NodeLog()

        # Volatile state
        self._commit_index = -1
        self._last_applied = -1

        # Volatile state for leaders
        self._next_index = {}
        self._match_index = {}

    async def start(self) -> None:
        node_address, node_port = self._node_config.get_node_info(self._name).as_tuple()

        await self._event_handler.start(node_address, node_port)

    @overload
    async def _broadcast_message(
        self, msg: AppendEntriesMessage
    ) -> list[AppendEntriesResponse]: ...
    @overload
    async def _broadcast_message(
        self, msg: RequestVoteMessage
    ) -> list[RequestVoteResponse]: ...

    async def _broadcast_message(self, msg):
        # self._event_handler.send_message(addr, port, msg)

        tasks = [
            asyncio.create_task(
                self._event_handler.send_message(
                    other_node.address, other_node.port, msg
                )
            )
            for other_node in self._node_config.get_other_nodes(self._name)
        ]

        responses = await asyncio.gather(*tasks)

        return [
            response
            for response in responses
            if not isinstance(response, TimeoutResponse)
        ]

    async def send_append_entries(
        self,
        host: str,
        port: int,
        entries: list,
        prev_log_index: int = -1,
        prev_log_term: int = -1,
    ) -> AppendEntriesResponse | TimeoutResponse:
        return await self._event_handler.send_message(
            host,
            port,
            AppendEntriesMessage(
                msg_type=MessageType.APPEND_ENTRIES,
                sender_term=self._current_term,
                sender_id=self._name,
                prev_log_index=prev_log_index,
                prev_log_term=prev_log_term,
                entries=entries,
                leader_commit=self._commit_index,
            ),
        )

    async def broadcast_append_entries(
        self, entries: list
    ) -> list[AppendEntriesResponse]:
        return await self._broadcast_message(
            AppendEntriesMessage(
                msg_type=MessageType.APPEND_ENTRIES,
                sender_term=self._current_term,
                sender_id=self._name,
                prev_log_index=0,
                prev_log_term=0,
                entries=entries,
                leader_commit=self._commit_index,
            )
        )

    async def broadcast_request_vote(self) -> list[RequestVoteResponse]:
        return await self._broadcast_message(
            RequestVoteMessage(
                msg_type=MessageType.REQUEST_VOTE,
                sender_term=self._current_term,
                sender_id=self._name,
                prev_log_index=0,
                prev_log_term=0,
            )
        )

    # State transitions
    def become_candidate(self) -> None:
        print("Become CANDIDATE")

        self._state = NodeState.CANDIDATE
        self._current_term += 1
        self._voted_for = self._name

    def become_leader(self) -> None:
        print("Become LEADER")

        self._state = NodeState.LEADER

        for node in self._node_config.nodes:
            self._next_index[node] = len(self._log)
            self._match_index[node] = -1

    def become_follower(self, term: int, voted_for: str | None) -> None:
        print("Become FOLLOWER")

        self._state = NodeState.FOLLOWER
        self._current_term = term
        self._voted_for = voted_for

    # Node timeouts
    async def heartbeat_timeout_elapsed(self) -> None:
        print(
            f"S: {self._storage} L: {self._log._log} CI: {self._commit_index} LA: {self._last_applied}"
        )

        if self._commit_index > self._last_applied:
            ...

        if self._state == NodeState.LEADER:
            self._event_handler.reschedule_election_timeout()

            # await self.broadcast_append_entries([])

            async def send_ae_to_follower(name: str, node_info: NodeInfo):
                if len(self._log) == 0:
                    await self.send_append_entries(
                        node_info.address,
                        node_info.port,
                        [],
                    )

                    return

                next_idx = self._next_index[name]
                prev_log_index = next_idx - 1
                prev_log_entry_term, _ = self._log._log[prev_log_index]
                prev_log_term = (
                    prev_log_entry_term
                    if prev_log_index >= 0 and prev_log_index < len(self._log)
                    else -1
                )
                new_entries = self._log._log[next_idx:]

                response = await self.send_append_entries(
                    node_info.address,
                    node_info.port,
                    new_entries,
                    prev_log_index=prev_log_index,
                    prev_log_term=prev_log_term,
                )

                if not isinstance(response, TimeoutResponse) and response.success:
                    self._match_index[name] = next_idx + len(new_entries) - 1
                    self._next_index[name] = self._match_index[name] + 1
                else:
                    self._next_index[name] = max(0, next_idx - 1)

            tasks = [
                asyncio.create_task(send_ae_to_follower(name, node_info))
                for name, node_info in self._node_config.nodes.items()
                if name != self._name
            ]

            await asyncio.gather(*tasks)

            replicated_count = 1  # Self
            for name, _ in self._node_config.nodes.items():
                if name != self._name:
                    if self._match_index.get(name, -1) >= self._log.last_idx():
                        replicated_count += 1

            if replicated_count > (self._node_config.get_node_count() // 2):
                self._commit_index = self._log.last_idx()
                self._apply_log()

    async def election_timeout_elapsed(self) -> None:
        print("Initiate ВЫБОРЫ")

        self.become_candidate()

        responses = await self.broadcast_request_vote()
        responses.append(
            RequestVoteResponse(term=self._current_term, vote_granted=True)
        )  # Self

        voted_for = len(
            [
                response.vote_granted
                for response in responses
                if response.vote_granted is True
            ]
        )

        if voted_for > (self._node_config.get_node_count() // 2):
            self.become_leader()
            await self.broadcast_append_entries([])

    # Local IO
    async def handle_terminal(self, string: str) -> None:
        print("We entered:", string)

    # Messages
    async def on_raft_message(self, msg: RaftMessage) -> None:
        self._event_handler.reschedule_election_timeout()

        if msg.sender_term > self._current_term and self._state != NodeState.FOLLOWER:
            # self.become_follower(msg.sender_term, None)
            self.become_follower(self._current_term, None)

    async def handle_append_entries(
        self, msg: AppendEntriesMessage
    ) -> AppendEntriesResponse:

        # print("Got AE ", msg)

        # 1
        if msg.sender_term < self._current_term:
            print("Fail AE at 1")
            return AppendEntriesResponse(term=self._current_term, success=False)

        # 2
        if msg.prev_log_index >= 0:
            entry = self._log.get(msg.prev_log_index)
            if entry is None:
                print("Fail AE at 2: entry is None")
                return AppendEntriesResponse(term=self._current_term, success=False)
            else:
                term, _ = entry
                if term != msg.prev_log_term:
                    print("Fail AE at 2")
                    return AppendEntriesResponse(term=self._current_term, success=False)

        # 3, 4
        for term, entry in msg.entries:
            if len(self._log) > msg.prev_log_index + 1 and (
                (log_entry := self._log.get(msg.prev_log_index + 1)) is not None
            ):
                log_term, _ = log_entry
                if log_term != term:
                    self._log.truncate(msg.prev_log_index + 1)
                    self._log.append(term, entry)
            else:
                self._log.append(term, entry)
            print(f"Add {entry} to log on follower")

        # 5
        if msg.leader_commit > self._commit_index:
            self._commit_index = min(msg.leader_commit, self._log.last_idx())
            self._apply_log()

        # print("AE Success")
        return AppendEntriesResponse(term=self._current_term, success=True)

    async def handle_request_vote(self, msg: RequestVoteMessage) -> RequestVoteResponse:
        if msg.sender_term > self._current_term and self._voted_for is None:
            self._current_term = msg.sender_term
            self._voted_for = msg.sender_id
            print(f"Vote for {msg.sender_id}")
            return RequestVoteResponse(term=self._current_term, vote_granted=True)
        else:
            print(f"Don't vote for {msg.sender_id}")
            return RequestVoteResponse(term=self._current_term, vote_granted=False)

    def _apply_log(self):
        while self._last_applied < self._commit_index:
            self._last_applied += 1
            entry = self._log.get(self._last_applied)

            if entry is not None:
                _, cmd = entry

                self._apply_command_to_state_machine(cmd)
            else:
                print("Error in _apply_log: entry is None")

            print(f"Apply {cmd}")

    def _apply_command_to_state_machine(self, cmd: StateMachineCommand):
        match cmd:
            case SetCommand(key, value):
                self._storage.set(key, value)

            case DeleteCommand(key):
                self._storage.delete(key)

    async def _execute_client_command(self, cmd: BaseCommand) -> ClientResponse:
        match cmd:
            case SetCommand(key, value):
                print(f"Add {cmd} to log on leader")
                self._log.append(self._current_term, cmd)

                return ClientResponse(text=f"Set {key}={value}")

            case QueryCommand(key):
                return ClientResponse(text=str(self._storage.query(key)))

            case DeleteCommand(key):
                print(f"Add {cmd} to log on leader")
                self._log.append(self._current_term, cmd)

                return ClientResponse(text=f"Delete {key}")

            case c:
                return ClientResponse(text=f"Unknown command {c}")

    async def handle_client_message(self, msg: ClientMessage) -> ClientResponse:
        try:
            cmd = parse_command(msg.text)
        except Exception as e:
            return ClientResponse(text=str(e))

        match self._state:
            case NodeState.FOLLOWER:
                match cmd:
                    case QueryCommand(key):
                        return ClientResponse(text=str(self._storage.query(key)))

                    case _:
                        return ClientResponse(
                            text="Can't process request: Send this response to leader"
                        )

            case NodeState.CANDIDATE:
                return ClientResponse(
                    text="Can't process request: Node is in a candidate state"
                )

            case NodeState.LEADER:
                return await self._execute_client_command(cmd)
