from antlr4.ParserRuleContext import ParserRuleContext
from typing import Callable, TypedDict, TypeVar


class FunctionDefinition(TypedDict):
    type: str
    handle: ParserRuleContext | Callable


T = TypeVar('T', bound='SymbolTable')


class SymbolTable:
    def __init__(self: T) -> None:
        # Maps name -> the actual ParseTree node for that sub/function
        self.definitions: dict[str, FunctionDefinition] = {}
