import asyncio
import json
from types import SimpleNamespace
from typing import overload
from pyraft.event import EventHandler
from pyraft.node.messages import (
    AppendEntriesMessage,
    AppendEntriesResponse,
    MessageType,
    RequestVoteMessage,
    RequestVoteResponse,
    TimeoutResponse,
)
from pyraft.transport.socket import MessageTransport


class EventManager:
    def __init__(
        self,
        transport: MessageTransport,
        heartbeat_timeout: int = 1,
        election_timeout: int = 5,
    ) -> None:
        self._transport = transport
        self._transport.register_message_callback(self.message_callback)

        self._heartbeat_timeout = heartbeat_timeout
        self._election_timeout = election_timeout

    def register_event_handler(self, event_handler: EventHandler) -> None:
        self._event_handler = event_handler

    async def message_callback(self, message: str) -> str:
        obj = json.loads(message, object_hook=lambda d: SimpleNamespace(**d))

        match obj.msg_type:
            case MessageType.APPEND_ENTRIES:
                response = await self._event_handler.handle_append_entries(obj)
            case MessageType.REQUEST_VOTE:
                response = await self._event_handler.handle_request_vote(obj)
            case _:
                raise RuntimeError("Unknown message:" + str(obj))

        return json.dumps(response.__dict__)

    @overload
    async def send_message(
        self, host: str, port: int, message: AppendEntriesMessage
    ) -> AppendEntriesResponse | TimeoutResponse: ...
    @overload
    async def send_message(
        self, host: str, port: int, message: RequestVoteMessage
    ) -> RequestVoteResponse | TimeoutResponse: ...

    async def send_message(self, host: str, port: int, message):
        try:
            response = await self._send_plain_message_with_timeout(
                host, port, json.dumps(message.__dict__)
            )

            obj = json.loads(response, object_hook=lambda d: SimpleNamespace(**d))
        except TimeoutError:
            obj = TimeoutResponse()
        except:
            obj = TimeoutResponse()

        return obj

    # async def send_plain_message(self, host: str, port: int, message: str) -> str:
    #     #return await self._transport.send_message(host, port, message)
    #     try:
    #         return await self.send_plain_message_with_timeout(host, port, message)
    #     except TimeoutError:
    #         return ""

    async def _send_plain_message_with_timeout(
        self, host: str, port: int, message: str
    ) -> str:
        try:
            print(f"Send message to {host}:{port}")
            async with asyncio.timeout(1):
                return await self._transport.send_message(host, port, message)
        except TimeoutError:
            print(f"Cannot reach {host}:{port}")
            raise

    async def heartbeat_loop(self):
        while True:
            try:
                async with asyncio.timeout(self._heartbeat_timeout) as ctx:
                    self._heartbeat_timeout_manager = ctx
                    await asyncio.sleep(self._heartbeat_timeout * 10)
            except TimeoutError:
                await self._event_handler.heartbeat_timeout_elapsed()

    def reschedule_heartbeat_timeout(self):
        if (
            self._heartbeat_timeout_manager
            and not self._heartbeat_timeout_manager.expired()
        ):
            new_timeout = asyncio.get_running_loop().time() + self._heartbeat_timeout
            self._heartbeat_timeout_manager.reschedule(new_timeout)

    async def election_loop(self):
        while True:
            try:
                async with asyncio.timeout(self._election_timeout) as ctx:
                    self._election_timeout_manager = ctx
                    await asyncio.sleep(self._election_timeout * 10)
            except TimeoutError:
                await self._event_handler.election_timeout_elapsed()

    def reschedule_election_timeout(self):
        if (
            self._election_timeout_manager
            and not self._election_timeout_manager.expired()
        ):
            new_timeout = asyncio.get_running_loop().time() + self._election_timeout
            self._election_timeout_manager.reschedule(new_timeout)

    async def input_loop(self):
        while True:
            data = await asyncio.to_thread(input)

            await self._event_handler.handle_terminal(data)

    async def start(self, address: str, port: int) -> None:
        heartbeat_task = asyncio.create_task(self.heartbeat_loop())
        election_task = asyncio.create_task(self.election_loop())
        input_task = asyncio.create_task(self.input_loop())
        server_task = asyncio.create_task(self._transport.start_server(address, port))

        await asyncio.gather(heartbeat_task, election_task, input_task, server_task)
