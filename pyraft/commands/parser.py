from pyraft.commands.exceptions import ParseException
from pyraft.commands.types import BaseCommand, DeleteCommand, QueryCommand, SetCommand


def parse_command(cmd: str) -> BaseCommand:
    tokens = cmd.split(" ")
    tokens = [token.strip() for token in tokens]

    match tokens:
        case ["s" | "set", key, value]:
            return SetCommand(key, value)
        case ["q" | "query", key]:
            return QueryCommand(key)
        case ["d" | "delete", key]:
            return DeleteCommand(key)
        case [cmd, *args]: # if cmd != ""
            raise ParseException(f"Invalid command {cmd} with arguments {args}")
        case t:
            raise ParseException(f"Invalid token sequence {t}")
