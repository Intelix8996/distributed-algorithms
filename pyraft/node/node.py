import asyncio
import random
from typing import overload
from pyraft.event import EventManager
from pyraft.node.messages import (
    AppendEntriesMessage,
    AppendEntriesResponse,
    MessageType,
    RequestVoteMessage,
    RequestVoteResponse,
    TimeoutResponse,
)
from pyraft.node.config import NodeConifg
from pyraft.node.state import NodeState
from pyraft.transport.socket import MessageTransport

ELECTION_TIMEOUT = 5
ELECTION_TIMEOUT_RANGE = 3


class Node:
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

        self._state = initial_state
        self._term = term
        self._voted_for = voted_for

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

        # for other_node in self._node_config.get_other_nodes(self._name):
        #     addr, port = other_node.as_tuple()

        #     try:
        #         print(f"Send heartbeat to {addr}:{port}")
        #         async with asyncio.timeout(1):
        #             await self._event_handler.send_message(addr, port, msg)
        #     except TimeoutError:
        #         print(f"Cannot reach {addr}:{port}")

    async def broadcast_append_entries(
        self, entries: list
    ) -> list[AppendEntriesResponse]:
        return await self._broadcast_message(
            AppendEntriesMessage(
                MessageType.APPEND_ENTRIES, self._name, self._term, entries
            )
        )

    async def broadcast_request_vote(self) -> list[RequestVoteResponse]:
        return await self._broadcast_message(
            RequestVoteMessage(MessageType.REQUEST_VOTE, self._name, self._term)
        )

    # State transitions
    def become_candidate(self) -> None:
        self._state = NodeState.CANDIDATE
        self._term += 1
        self._voted_for = self._name

    def become_leader(self) -> None:
        self._state = NodeState.LEADER

    def become_follower(self, term: int, voted_for: str) -> None:
        self._state = NodeState.FOLLOWER
        self._term = term
        self._voted_for = voted_for

    # Node timeouts
    async def heartbeat_timeout_elapsed(self) -> None:
        if self._state == NodeState.LEADER:
            self._event_handler.reschedule_election_timeout()
            await self.broadcast_append_entries([])

    async def election_timeout_elapsed(self) -> None:
        print("ВЫБОРЫ")

        self.become_candidate()

        responses = await self.broadcast_request_vote()
        responses.append(RequestVoteResponse(True))  # Self

        voted_for = len(
            [response.vote for response in responses if response.vote is True]
        )

        if voted_for > (len(responses) // 2):
            self.become_leader()

    # Local IO
    async def handle_terminal(self, string: str) -> None:
        print("We entered:", string)

    # Messages
    async def handle_append_entries(
        self, msg: AppendEntriesMessage
    ) -> AppendEntriesResponse:
        self._event_handler.reschedule_election_timeout()

        self._voted_for = None
        if msg.sender_term > self._term:
            self._term = msg.sender_term

        if self._state == NodeState.CANDIDATE:
            self._state = NodeState.FOLLOWER

        return AppendEntriesResponse()

    async def handle_request_vote(self, msg: RequestVoteMessage) -> RequestVoteResponse:
        self._event_handler.reschedule_election_timeout()

        if msg.sender_term > self._term and self._voted_for is None:
            self._term = msg.sender_term
            self._voted_for = msg.sender
            return RequestVoteResponse(True)
        else:
            return RequestVoteResponse(False)
