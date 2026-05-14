from antlr4_vba.vbaParser import vbaParser as Parser
from typing import Any, Callable, TypedDict, TypeVar


class ParamDefinition(TypedDict):
    name: str
    optional: bool
    default: Any


class FunctionBase(TypedDict):
    type: str
    project: str
    module: str
    extra: dict[str, Any]


class FunctionDefinition(FunctionBase):
    name: str
    handle: (
        Parser.FunctionDeclarationContext |
        Parser.SubroutineDeclarationContext
    )
    params: list[ParamDefinition]


class LibraryDefinition(FunctionBase):
    name: str
    handle: Callable
    params: list[ParamDefinition]


class ModuleDefinition(TypedDict):
    name: str
    type: str
    functions: dict[str, FunctionDefinition]
    extra: dict[str, Any]


class LibModuleDefinition(TypedDict):
    name: str
    type: str
    functions: dict[str, LibraryDefinition]


class ProjectDefinition(TypedDict):
    name: str
    type: str
    modules: dict[str, ModuleDefinition]
    extra: dict[str, Any]


class LibProjectDefinition(TypedDict):
    name: str
    type: str
    modules: dict[str, LibModuleDefinition]
    classes: dict[str, LibModuleDefinition]


T = TypeVar('T', bound='SymbolTable')


class SymbolTable:
    def __init__(self: T) -> None:
        # Maps module name -> function name -> the actual ParseTree node
        # for that sub/function
        self.definitions: dict[str, ProjectDefinition] = {}
        self.library_definitions: dict[str, LibProjectDefinition] = {}
