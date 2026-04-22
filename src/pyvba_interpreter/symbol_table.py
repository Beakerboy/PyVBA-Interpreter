from antlr4.ParserRuleContext import ProcedureBodyContext
from typing import Any, Callable, TypedDict, TypeVar


class ParamDefinition(TypedDict):
    name: str
    optional: bool
    default: Any


class FunctionDefinition(TypedDict):
    type: str
    handle: ProcedureBodyContext | None
    params: list[ParamDefinition]


class LibraryDefinition(TypedDict):
    type: str
    handle: Callable


T = TypeVar('T', bound='SymbolTable')


class SymbolTable:
    def __init__(self: T) -> None:
        # Maps name -> the actual ParseTree node for that sub/function
        self.definitions: dict[str, FunctionDefinition] = {}
        self.library_definitions: dict[str, LibraryDefinition] = {}
