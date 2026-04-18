from typing import TypeVar
from .symbol_table import SymbolTable


T = TypeVar('T', bound='VbaListener')


class VbaListener(VBAListener):
    def __init__(self: T, table: SymbolTable):
        self.table = table

    def enterSubStmt(self, ctx):
        name = ctx.IDENTIFIER().getText()
        # Save the context (subtree) so the Visitor can find it later
        self.table.definitions[name] = ctx
