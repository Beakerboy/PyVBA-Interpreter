from typing import Any, TypeVar
from antlr4_vba.vbaParser import vbaParser as Parser
from antlr4_vba.vbaParserVisitor import vbaParserVisitor as Visitor
from vba_stdlib.literal_factory import literal_from_string
from .symbol_table import SymbolTable


T = TypeVar('T', bound='VbaVisitor')


class VbaVisitor(Visitor):

    def __init__(self: T, table: SymbolTable) -> None:
        self.functions = table

    def visitCallStatement(                                        # noqa: N802
            self: T,
            ctx: Parser.CallStatementContext) -> None:
        command = ''
        if ctx.getChild(0).getText().lower() == "call":
            command = ctx.indexExpression().lExpression().getText()
            args = self.visit(ctx.indexExpression().argumentList())
        else:
            command = ctx.getChild(0).getText()
            args = self.visit(ctx.argumentList())
        if command.lower() == "msgbox":
            try:
                string = str(args[0])
            except Exception:
                raise Exception("Value cannot be cast to a string")
            print(string)

    def visitArgumentList(                                         # noqa: N802
            self: T,
            ctx: Parser.ArgumentListContext) -> list[Any]:
        args = []
        for child in ctx.children:
            if child is not None:
                args += [self.visit(child)]
        return args

    def visitLiteralExpression(                                    # noqa: N802
            self: T,
            ctx: Parser.LiteralExpressionContext) -> Any:
        return literal_from_string(ctx.getText())

    def visitExpression(                                           # noqa: N802
            self: T,
            ctx: Parser.ExpressionContext) -> Any:
        number = ctx.getAltNumber()
        if number in [5, 7, 8, 9, 10, 11, 13]:
            left = self.visit(ctx.expression(0))
            right = self.visit(ctx.expression(1))
            op = ctx.getChild(1).symbol.text
            if op == '^':
                return left ^ right
            if op == '*':
                return left * right
            if op == '/':
                return left / right
            if op == '+':
                return left + right
            if op == '-':
                return left - right
        return self.visitChildren(ctx)

    def visitUnaryMinusExpression(                                 # noqa: N802
            self: T,
            ctx: Parser.UnaryMinusExpressionContext) -> int | float:
        value = self.visit(ctx.expression())
        return -1 * value
