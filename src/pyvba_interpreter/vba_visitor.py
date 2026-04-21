from typing import Any, TypeVar
from antlr4_vba.vbaParser import ParserRuleContext, vbaParser as Parser
from antlr4_vba.vbaParserVisitor import vbaParserVisitor as Visitor
from vba_stdlib.literal_factory import literal_from_string
from .symbol_table import SymbolTable
from .Exceptions.vba_compile_exception import VbaCompileException


T = TypeVar('T', bound='VbaVisitor')


class VbaVisitor(Visitor):

    def __init__(self: T, table: SymbolTable) -> None:
        self.table = table

    @staticmethod
    def _get_op(ctx: ParserRuleContext) -> str:
        i = 1
        if isinstance(ctx.getChild(1), Parser.WscContext):
            i = 2
        return ctx.getChild(i).symbol.text

    def visitCallStatement(                                        # noqa: N802
            self: T,
            ctx: Parser.CallStatementContext) -> None:
        command = ''
        if ctx.getChild(0).getText().lower() == "call":
            command = ctx.indexExpression().lExpression().getText().lower()
            args = self.visit(ctx.indexExpression().argumentList())
        else:
            command = ctx.simpleNameExpression().getText().lower()
            args = self.visit(ctx.argumentList())
        if command not in self.table.definitions:
            raise VbaCompileException("Sub or Function not defined")
        func_info = self.table.definitions.get(command)
        if func_info and func_info["type"] == "builtin":
            return func_info["handle"](*args)

    def visitArgumentList(                                         # noqa: N802
            self: T,
            ctx: Parser.ArgumentListContext) -> list[Any]:
        args = []
        if ctx.children is not None:
            for child in ctx.children:
                if child is not None:
                    args += [self.visit(child)]
        return args

    def visitLiteralExpression(                                    # noqa: N802
            self: T,
            ctx: Parser.LiteralExpressionContext) -> Any:
        return literal_from_string(ctx.getText())

    def visitArithmeticExpression(                                 # noqa: N802
            self: T,
            ctx: Parser.ArithmeticExpressionContext) -> Any:
        left = self.visit(ctx.getChild(0))
        assert left is not None
        last = ctx.getChildCount() - 1
        right = self.visit(ctx.getChild(last))
        assert right is not None
        op = self._get_op(ctx)
        if op == '*':
            return left * right
        elif op == '/':
            return left / right
        elif op == '+':
            return left + right
        elif op == '-':
            return left - right
        elif op == '^':
            return left ** right
        elif op.upper() == 'MOD':
            return left % right
        else:  # op == '\\':
            return left // right

    def visitUnaryMinusExpression(                                 # noqa: N802
            self: T,
            ctx: Parser.UnaryMinusExpressionContext) -> int | float:
        value = self.visit(ctx.expression())
        return -1 * value

    def visitRelationExpression(                                   # noqa: N802
            self: T,
            ctx: Parser.RelationExpressionContext
    ) -> bool:
        left = self.visit(ctx.getChild(0))
        last = ctx.getChildCount() - 1
        right = self.visit(ctx.getChild(last))
        assert left is not None
        assert right is not None
        op = self._get_op(ctx)
        if op == '<':
            return left < right
        elif op == '>':
            return left > right
        elif op == '=':
            return left == right
        elif op == '<>' or op == '><':
            return left != right
        elif op == '>=' or op == '=>':
            return left >= right
        elif op == '<=' or op == '=<':
            return left <= right
        else:  # LIKE
            raise Exception("Currently Unsupported")

    def visitBooleanExpress(                                    # noqa: N802
            self: T,
            ctx: Parser.BooleanExpressContext) -> bool:
        left = self.visit(ctx.getChild(0))
        last = ctx.getChildCount() - 1
        right = self.visit(ctx.getChild(last))
        assert left is not None
        assert right is not None
        op = self._get_op(ctx).upper()
        if op == "AND":
            return left and right
        elif op == "OR":
            return left or right
        elif op == "XOR":
            return left != right
        elif op == "IMP":
            return not left or right
        else:  # op == "EQV":
            return left == right

    def vistIndexExpress(                                       # noqa: N802
            self: T,
            ctx: Parser.IndexExpressContext) -> Any:
        raise VbaCompileException("")
        return self._visit_shared_index_expression(ctx)

    def vistIndexExpression(                                    # noqa: N802
            self: T,
            ctx: Parser.IndexExpressionContext) -> Any:
        return self._visit_shared_index_expression(ctx)

    def _visit_shared_index_expression(
            self: T,
            ctx: (
                Parser.IndexExpressContext |
                Parser.IndexExpressionContext
            )) -> Any:
        name = ctx.getChild(0).getText().lower()
        if name not in self.table.definitions:
            raise VbaCompileException("Sub or Function not defined")
        definition = self.table.definitions[name]
        if definition["type"] == "sub":
            raise VbaCompileException("Unexpected Function or variable")
