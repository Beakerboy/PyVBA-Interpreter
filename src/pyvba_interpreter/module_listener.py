"""
Listener responsible for discovering declarations within VBA standard
modules.

This listener registers module-level procedures and stores the associated
parse-tree handles for later execution by visitors.
"""
from __future__ import annotations
from typing import TypeVar

from antlr4_vba.vbaParser import vbaParser as Parser

from .base_listener import BaseListener
from .symbol_table import SymbolTable
from .Exceptions.vba_compile_exception import VbaCompileException
from .Exceptions.vba_exception import VbaException

T = TypeVar("T", bound="ModuleListener")


class ModuleListener(BaseListener):
    """
    Listener used to process VBA standard modules.
    """

    def __init__(self: T, project: str, table: SymbolTable) -> None:
        super().__init__(project, table)
        self.module_name = ""

    def enterProceduralModuleHeader(                               # noqa: N802
            self: T,
            ctx: Parser.ProceduralModuleHeaderContext) -> None:
        """
        Register a module within the current project.
        """
        self.module_name = ctx.STRINGLITERAL().getText()[1:-1]

        if self.module_name.lower() == "vba":
            raise VbaException(
                "Name conflicts with existing module, project, "
                "or object library"
            )

        project = self.table.definitions[self.project_name]

        project["modules"][self.module_name.lower()] = {
            "name": self.module_name.lower(),
            "type": "module",
            "functions": {},
            "extra": {}
        }

    def enterFunctionDeclaration(                                  # noqa: N802
            self: T,
            ctx: Parser.FunctionDeclarationContext) -> None:
        """
        Register a Function declaration.
        """
        name = ctx.functionName().getText()

        modules = self.table.definitions[self.project_name]["modules"]

        funcs = modules[self.module_name.lower()]["functions"]

        if name.lower() in funcs:
            raise VbaCompileException(
                f"Ambiguous name detected: {name}"
            )

        funcs[name.lower()] = {
            "name": name.lower(),
            "type": "function",
            "project": self.project_name,
            "module": self.module_name.lower(),
            "handle": ctx,
            "params": self._get_params(
                ctx.procedureParameters()
            ),
            "extra": {}
        }

    def enterSubroutineDeclaration(                                # noqa: N802
            self: T,
            ctx: Parser.SubroutineDeclarationContext) -> None:
        """
        Register a Sub declaration.
        """
        name = ctx.subroutineName().getText()

        modules = self.table.definitions[self.project_name]["modules"]

        funcs = modules[self.module_name.lower()]["functions"]

        if name.lower() in funcs:
            raise VbaCompileException(
                f"Ambiguous name detected: {name}"
            )

        funcs[name.lower()] = {
            "name": name.lower(),
            "type": "sub",
            "project": self.project_name,
            "module": self.module_name.lower(),
            "handle": ctx,
            "params": self._get_params(
                ctx.procedureParameters()
            ),
            "extra": {}
        }
