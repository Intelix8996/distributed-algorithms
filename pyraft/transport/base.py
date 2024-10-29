from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable


class MessageTransport(ABC):

    def register_message_callback(
        self, message_callback: Callable[[str], Awaitable[str]]
    ) -> None:
        self._message_callback = message_callback

    @abstractmethod
    async def send_message(self, host: str, port: int, msg: str) -> str: ...

    @abstractmethod
    async def start_server(self, host: str, port: int) -> None: ...
