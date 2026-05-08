from antlr4_vba.vbaParser import vbaParser as Parser
from enum import Enum
from typing import Any, Callable, TypedDict, TypeVar


class FunctionType(Enum):
    PROJECT = 0
    MODULE = 1
    FUNCTION = 2
    SUB = 3
    PROPERTY = 4


class ParamDefinition(TypedDict):
    name: str
    optional: bool
    default: Any


class FunctionBase(TypedDict):
    type: FunctionType
    project: str
    module: str


class FunctionDefinition(FunctionBase):
    name: str
    handle: Parser.FunctionDefinitionContext | Parser.SubroutineDefinitionContext
    params: list[ParamDefinition]


class LibraryDefinition(FunctionBase):
    name: str
    handle: Callable
    params: list[ParamDefinition]


class ModuleDefinition(TypedDict):
    name: str
    type: FunctionType
    functions: dict[str, FunctionDefinition]


class LibModuleDefinition(TypedDict):
    name: str
    type: FunctionType
    functions: dict[str, LibraryDefinition]


class ProjectDefinition(TypedDict):
    name: str
    type: FunctionType
    modules: dict[str, ModuleDefinition]


class LibProjectDefinition(TypedDict):
    name: str
    type: FunctionType
    modules: dict[str, LibModuleDefinition]


T = TypeVar('T', bound='SymbolTable')


class SymbolTable:
    def __init__(self: T) -> None:
        # Maps module name -> function name -> the actual ParseTree node
        # for that sub/function
        self.definitions: dict[str, ProjectDefinition] = {}
        self.library_definitions: dict[str, LibProjectDefinition] = {}
