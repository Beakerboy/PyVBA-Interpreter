from typing import TypeVar
from antlr4_vba.vbaParserVisitor import vbaParserVisitor as Visitor
from antlr4_vba.vbaParserListener import vbaParserListener as Listener
from .symbol_table import SymbolTable


T = TypeVar('T', bound='VbaListener')


class VbaListener(Listener):
    def __init__(self: T, table: SymbolTable) -> None:
        self.table = table

    def enterFunctionDeclaration(                                  # noqa: N802
            self: T,
            ctx: Parser.FunctionDeclaration) -> None:
        name = ctx.functionName().getText()
        # Save the context (subtree) so the Visitor can find it later
        self.table.definitions[name] = ctx
