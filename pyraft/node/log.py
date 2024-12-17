from pyraft.commands.types import StateMachineCommand

LogEntry = tuple[int, StateMachineCommand]

class NodeLog:
    _log: list[LogEntry]

    def __init__(self) -> None:
        self._log = []

    def append(self, term: int, cmd: StateMachineCommand):
        self._log.append((term, cmd))

    def get(self, idx: int) -> LogEntry | None:
        try:
            return self._log[idx]
        except IndexError:
            return None

    def last_idx(self) -> int:
        return len(self._log) - 1
    
    def truncate(self, idx: int) -> None:
        self._log = self._log[:idx]

    def __len__(self) -> int:
        return len(self._log)
