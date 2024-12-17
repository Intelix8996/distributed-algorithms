from pydantic.dataclasses import dataclass

@dataclass
class BaseCommand: ...

@dataclass
class QueryCommand(BaseCommand):
    key: str

@dataclass
class StateMachineCommand(BaseCommand): ...

@dataclass
class SetCommand(StateMachineCommand):
    key: str
    value: str

@dataclass
class DeleteCommand(StateMachineCommand):
    key: str
