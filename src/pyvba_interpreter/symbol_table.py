from antlr4_vba.vbaParser import vbaParser as Parser
from enum import Enum
from typing import Any, Callable, TypedDict, TypeVar


class FunctionType(Enum):
    FUNCTION = 0
    SUB = 1
    PROPERTY = 2
    PROJECT = 3
    MODULE = 4


class ParamDefinition(TypedDict):
    name: str
    optional: bool
    default: Any


class FunctionBase(TypedDict):
    type: FunctionType
    module: str


class FunctionDefinition(FunctionBase):
    handle: Parser.ProcedureBodyContext | None
    params: list[ParamDefinition]


class LibraryDefinition(FunctionBase):
    handle: Callable
    params: list[ParamDefinition]


T = TypeVar('T', bound='SymbolTable')


class SymbolTable:
    def __init__(self: T) -> None:
        # Maps module name -> function name -> the actual ParseTree node
        # for that sub/function
        self.definitions: dict[str, [dict[str, dict[str, FunctionDefinition]]] = {}
        self.library_definitions: dict[str, [dict[str, dict[str, LibraryDefinition]]] = {}
